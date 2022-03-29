import argparse
import asyncio
import logging
import sys
from asyncio import Queue, Event, CancelledError, TimeoutError
from contextlib import suppress

import aiohttp
import motor.motor_asyncio
from aiohttp import ClientSession
from codetiming import Timer
from motor.motor_asyncio import AsyncIOMotorCollection
from tqdm.asyncio import tqdm

from src.common import global_db_name, connect_mongo
from src.scrape import JobQueue, UsernameJob, PageJob, PlayerRecord, RequestFailed, UserNotFound, get_page_range, \
    get_hiscores_page, get_player_stats, mongodoc_to_player, player_to_mongodoc, reset_vpn, getsudo, askpass, \
    print_and_log


N_PAGE_WORKERS = 2  # number of page workers downloading rank/username info
UNAME_BUFSIZE = 100 # maximum length of buffer containing username jobs for stats workers

currentpage = 0  # for page workers to coordinate in enqueueing their results
currentrank = 0  # for stats workers to coordinate in enqueueing their results


class DoneScraping(Exception):
    """ Raised when all scraping is done to indicate script should exit. """


class PageWorker:
    def __init__(self, in_queue: JobQueue, out_queue: JobQueue, name: str = None):
        self.name = name if name else type(self).__name__
        self.in_q = in_queue
        self.out_q = out_queue

    async def run(self, sess: ClientSession, next_page: Event):
        while True:
            job: PageJob = await self.in_q.get()
            try:
                if not job.pagecontents:
                    job.pagecontents = await get_hiscores_page(sess, page_num=job.pagenum)
                ranks, unames = job.pagecontents

                global currentpage
                while currentpage < job.pagenum:
                    await next_page.wait()
                    next_page.clear()

                for i in range(job.startind, job.endind):
                    out_job = UsernameJob(rank=ranks[i], username=unames[i])
                    await self.out_q.put(out_job)
                    job.startind += 1

                self.in_q.task_done()
                currentpage += 1
                next_page.set()

            except (CancelledError, RequestFailed):
                await self.in_q.put(job, force=True)
                self.in_q.task_done()
                raise


class StatsWorker:
    def __init__(self, in_queue: JobQueue, out_queue: JobQueue, name: str = None):
        self.name = name if name else type(self).__name__
        self.in_q = in_queue
        self.out_q = out_queue

    async def run(self, sess: ClientSession, next_user: Event, delay: float = 0):
        await asyncio.sleep(delay)
        while True:
            job: UsernameJob = await self.in_q.get()
            try:
                if not job.result:
                    try:
                        job.result = await get_player_stats(sess, username=job.username)
                    except UserNotFound:
                        job.result = 'notfound'

                global currentrank
                while currentrank < job.rank:
                    await next_user.wait()
                    next_user.clear()

                if job.result != 'notfound':
                    player: PlayerRecord = job.result
                    await self.out_q.put(player)

                self.in_q.task_done()
                currentrank += 1
                next_user.set()

            except (CancelledError, RequestFailed):
                await self.in_q.put(job, force=True)
                self.in_q.task_done()
                raise


async def export_records(in_queue: Queue, coll: AsyncIOMotorCollection):
    while True:
        # Release a batch every 50 records or 0.25 seconds of inactivity.
        players = []
        while len(players) < 50:
            try:
                next: PlayerRecord = await asyncio.wait_for(in_queue.get(), timeout=1)
                players.append(next)
            except TimeoutError:
                break
        if players:
            await coll.insert_many([player_to_mongodoc(p) for p in players])
            for _ in range(len(players)):
                in_queue.task_done()


async def track_progress(start_rank: int, end_rank: int, pageq: JobQueue, unameq: JobQueue, exportq: Queue):
    total = end_rank - start_rank + 1
    n = currentrank - start_rank
    with tqdm(initial=n, total=total) as pbar:
        while True:
            try:
                await asyncio.wait_for(asyncio.gather(pageq.join(), unameq.join(), exportq.join()), timeout=1)
                raise DoneScraping
            except TimeoutError:
                pass
            finally:
                pbar.n = currentrank - start_rank
                pbar.refresh()


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, loglevel: str = 'warning', usevpn: bool = True, drop: bool = False):

    logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                        datefmt="%H:%M:%S", level=getattr(logging, loglevel.upper()),
                        filename='scrape_hiscores.log', filemode='w')

    # Connect to MongoDB and check for existing progress.
    connect_mongo(mongo_url)
    coll = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print_and_log(f"dropped collection '{mongo_coll}'", level='info')

    highest_doc = await coll.find_one({}, sort=[('rank', -1)])
    if highest_doc:
        existing_rank = mongodoc_to_player(highest_doc).rank
        if existing_rank >= start_rank:
            print_and_log(f"found an existing record at rank {existing_rank}", level='info')
            if existing_rank >= stop_rank:
                print_and_log("nothing to do", level='info')
                return
            start_rank = existing_rank + 1
            print_and_log(f"starting from {start_rank}", level='info')

    # Get root permissions for VPN management.
    if usevpn:
        password = askpass()
        if not password:
            usevpn = False
        elif not getsudo(password):
            raise ValueError("sudo failed to authenticate")

    # Determine the range of pages that need to be scraped based on the desired range of ranks.
    firstpage, startind, lastpage, endind = get_page_range(start_rank, stop_rank)
    global currentpage, currentrank
    currentpage = firstpage
    currentrank = start_rank

    # Build the job queues connecting each stage of the processing pipeline.
    page_jobq = asyncio.PriorityQueue()
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(pagenum=pagenum,
                      startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        await page_jobq.put(job)
    uname_jobq = JobQueue(maxsize=UNAME_BUFSIZE)
    export_q = asyncio.Queue()

    # Create the workers for performing scraping tasks.
    export = asyncio.create_task(export_records(export_q, coll))
    pageworkers = [PageWorker(page_jobq, uname_jobq, name=f'page worker {i}') for i in range(N_PAGE_WORKERS)]
    statworkers = [StatsWorker(uname_jobq, export_q, name=f'stats worker {i}') for i in range(nworkers)]
    pageworker_signal = asyncio.Event()
    statworker_signal = asyncio.Event()

    print_and_log(f"starting to scrape (ranks {start_rank}-{stop_rank}, {nworkers} stats workers)", level='info')
    t = Timer(text="done ({minutes:.1f} minutes)")
    t.start()
    while True:
        if usevpn:
            logging.info(f"resetting VPN...")
            assert getsudo(password)
            reset_vpn()
            logging.info(f"successfully reset VPN")

        # Spawn the data scraping tasks and wait until requests start getting blocked.
        async with aiohttp.ClientSession() as sess:
            T = [asyncio.create_task(track_progress(start_rank, stop_rank, page_jobq, uname_jobq, export_q))]
            for w in pageworkers:
                T.append(asyncio.create_task(w.run(sess, next_page=pageworker_signal)))
            for i, w in enumerate(statworkers):
                T.append(asyncio.create_task(w.run(sess, next_user=statworker_signal, delay=i * 0.1)))

            try:
                await asyncio.gather(*T, export)  # allow first exception to be caught
            except DoneScraping:
                break
            except RequestFailed as e:
                logging.info(f"main: caught RequestFailed: {e}")
                continue
            except Exception:
                raise
            finally:
                for task in T:
                    task.cancel()
                await asyncio.gather(*T, return_exceptions=True)  # suppress CancelledErrors

    export.cancel()
    with suppress(CancelledError):
        await export
    t.stop()
    logging.info("done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Download player data from OSRS hiscores into MongoDB.""")
    parser.add_argument('--mongo-url', default="localhost:27017", help="store data in Mongo instance at this URL")
    parser.add_argument('--mongo-coll', default="scrape", help="put scraped data into this collection")
    parser.add_argument('--start-rank', default=1, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', default=2000000, type=int, help="stop data collection at this rank")
    parser.add_argument('--num-workers', default=28, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--log-level', default='warning', help="'debug'|'info'|'warning'|'error'|'critical'")
    parser.add_argument('--novpn', dest='usevpn', action='store_false', help="if set, will run without using VPN")
    parser.add_argument('--drop', action='store_true', help="if set, will drop collection before scrape begins")
    args = parser.parse_args()

    if args.num_workers + N_PAGE_WORKERS > 30:
        print_and_log(f"running with >{30 - N_PAGE_WORKERS} stats workers is not recommended. This will "
                      f"create more than 30 open connections at once, exceeding the remote server limit.",
                      level='warning')

    try:
        asyncio.run(main(args.mongo_url, args.mongo_coll, args.start_rank, args.stop_rank,
                         args.num_workers, args.log_level, args.usevpn, args.drop))
    except Exception as e:
        logging.critical(f"{type(e).__name__}: {e}")
        print(f"{e}, exiting")
        sys.exit(1)
