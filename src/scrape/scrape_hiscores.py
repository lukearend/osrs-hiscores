import argparse
import asyncio
import logging
import sys
import traceback
from asyncio import CancelledError, TimeoutError
from contextlib import suppress

import aiohttp
import motor.motor_asyncio
from codetiming import Timer
from motor.motor_asyncio import AsyncIOMotorCollection
from tqdm.asyncio import tqdm

from src.common import global_db_name, connect_mongo
from src.scrape import get_page_range, reset_vpn, getsudo, askpass, mongodoc_to_player, player_to_mongodoc, printlog
from src.scrape.requests import PlayerRecord, RequestFailed
from src.scrape.workers import JobCounter, JobQueue, PageWorker, StatsWorker, PageJob

N_PAGE_WORKERS = 2   # number of page workers downloading rank/username info
UNAME_BUFSIZE = 100  # maximum length of buffer containing username jobs for stats workers


class DoneScraping(Exception):
    """ Raised when all scraping is done to indicate script should exit. """


async def export_records(in_queue: JobQueue, coll: AsyncIOMotorCollection):
    while True:
        # Release a batch every 50 records or after a break in activity.
        players = []
        while len(players) < 50:
            try:
                next: PlayerRecord = await asyncio.wait_for(in_queue.get(), timeout=1)
                players.append(next)
            except TimeoutError:
                break
        if players:
            docs = [player_to_mongodoc(p) for p in players]
            await coll.insert_many(docs)
            in_queue.task_done(n=len(docs))


async def progress_bar(start_rank: int, end_rank: int, current_rank: JobCounter):
    total = end_rank - start_rank + 1
    ndone = current_rank.value - start_rank
    with tqdm(initial=ndone, total=total) as pbar:
        while True:
            await asyncio.sleep(1)
            pbar.n = current_rank.value - start_rank
            pbar.refresh()


async def detect_finished(*queues: JobQueue):
    await asyncio.gather(*[q.join() for q in queues])
    raise DoneScraping


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, loglevel: str = 'warning', usevpn: bool = True, drop: bool = False):

    logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                        datefmt="%H:%M:%S", level=getattr(logging, loglevel.upper()),
                        filename='scrape_hiscores.log', filemode='w')

    # The remote server seems to have a connection limit of 30.
    if args.num_workers + N_PAGE_WORKERS > 30:
        raise ValueError(f"too many workers, maximum allowed is {30 - N_PAGE_WORKERS}")

    # Connect to MongoDB and check for existing progress.
    connect_mongo(mongo_url)
    coll = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        printlog(f"dropped collection '{mongo_coll}'", level='info')

    highest_doc = await coll.find_one({}, sort=[('rank', -1)])
    if highest_doc:
        existing_rank = mongodoc_to_player(highest_doc).rank
        if existing_rank >= start_rank:
            printlog(f"found an existing record at rank {existing_rank}", level='info')
            if existing_rank >= stop_rank:
                printlog("nothing to do", level='info')
                return
            start_rank = existing_rank + 1
            printlog(f"starting from {start_rank}", level='info')

    # Get root permissions for VPN management.
    if usevpn:
        password = askpass()
        if not password:
            usevpn = False
        elif not getsudo(password):
            raise ValueError("sudo failed to authenticate")

    # Determine the range of pages that need to be scraped based on the desired range of ranks.
    firstpage, startind, lastpage, endind = get_page_range(start_rank, stop_rank)

    # Build the job queues connecting each stage of the processing pipeline.
    page_q = JobQueue()
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(priority=pagenum, pagenum=pagenum,
                      startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        await page_q.put(job)
    uname_q = JobQueue(maxsize=UNAME_BUFSIZE)
    export_q = JobQueue()

    # Scraping happens in two stages. First the page workers download front pages
    # of the hiscores and extract usernames in ranked order. Then the stats workers
    # receive usernames and query the CSV API for the corresponding account stats.
    pageworkers = [PageWorker(in_queue=page_q, out_queue=uname_q, init_page=firstpage,
                              name=f'page worker {i}') for i in range(N_PAGE_WORKERS)]
    statworkers = [StatsWorker(in_queue=uname_q, out_queue=export_q, init_rank=start_rank,
                               name=f'stats worker {i}') for i in range(nworkers)]
    currentrank: JobCounter = StatsWorker.currentrank

    export = asyncio.create_task(export_records(export_q, coll))
    isdone = asyncio.create_task(detect_finished(page_q, uname_q, export_q))

    printlog(f"starting to scrape (ranks {start_rank}-{stop_rank}, {nworkers} stats workers)", level='info')
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
            T = [asyncio.create_task(progress_bar(start_rank, stop_rank, current_rank=currentrank))]
            for w in pageworkers:
                T.append(asyncio.create_task(w.run(sess)))
            for i, w in enumerate(statworkers):
                T.append(asyncio.create_task(w.run(sess, delay=i * 0.1)))

            try:
                await asyncio.gather(*T, export, isdone)  # allow first exception to be caught
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

    try:
        asyncio.run(main(args.mongo_url, args.mongo_coll, args.start_rank, args.stop_rank,
                         args.num_workers, args.log_level, args.usevpn, args.drop))
    except Exception as e:
        logging.critical(traceback.format_exc())
        print(e)
        printlog("exiting", 'info')
        sys.exit(1)
