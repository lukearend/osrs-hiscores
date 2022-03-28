import argparse
import asyncio
import heapq
import logging
from asyncio import PriorityQueue, Queue, Event
from typing import List

import aiohttp
import motor.motor_asyncio
from aiohttp import ClientSession
from codetiming import Timer
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection
from tqdm.asyncio import tqdm

from src.common import global_db_name, connect_mongo
from src.scrape import UsernameJob, PageJob, PlayerRecord, RequestFailed, UserNotFound, get_page_range, \
    get_hiscores_page, get_player_stats, mongodoc_to_player, player_to_mongodoc, reset_vpn, getsudo, askpass


N_PAGE_WORKERS = 2   # number of page workers downloading rank/username info
UNAME_BUFSIZE = 100  # maximum length of buffer containing username jobs for stats workers
MAX_HEAPSIZE = 1000  # maximum size for the sorting heap before it allows records to be skipped

currentpage = 0  # for page workers to coordinate in enqueueing their results
nprocessed = 0   # for global progress bar


class DoneScraping(Exception):
    """ Raised when all scraping is done to indicate script should exit. """


async def page_worker(sess: ClientSession, page_queue: PriorityQueue, out_queue: PriorityQueue,
                      nextpage: Event, nextuname: Event, workernum: int = 0):
    name = f"page worker {workernum}"

    async def putback(job, unames_done=0):
        job.startind += unames_done
        await page_queue.put(job)
        page_queue.task_done()

    await asyncio.sleep(workernum * 0.25)
    global currentpage
    while True:
        job: PageJob = await page_queue.get()
        n_enqueued = 0
        try:
            if not job.result:
                try:
                    # Get rank/username data for the 25 players on the requested page.
                    job.result = await get_hiscores_page(sess, job.pagenum)
                except RequestFailed:
                    logging.info(f"{name}: caught RequestFailed, raising")
                    await putback(job)
                    raise

            # Wait until it is my turn to enqueue the page results.
            while currentpage != job.pagenum:
                await nextpage.wait()
                nextpage.clear()

            ranks, unames = job.result
            for i in range(job.startind, job.endind):
                while out_queue.qsize() >= UNAME_BUFSIZE:
                    await nextuname.wait()  # wait for signal to enqueue next username
                    nextuname.clear()
                await out_queue.put(UsernameJob(ranks[i], unames[i]))
                n_enqueued += 1

        # If interrupted, put the partially completed job back to be finished later.
        except asyncio.CancelledError:
            logging.debug(f"{name}: cancelled")
            await putback(job, unames_done=n_enqueued)
            raise

        # Let other worker(s) know this page was successfully enqueued.
        currentpage += 1
        page_queue.task_done()
        nextpage.set()


async def stats_worker(sess: ClientSession, uname_queue: PriorityQueue, out_queue: Queue,
                       nextuname: Event, workernum: int = 0):
    name = f"stats worker {workernum}"

    async def putout(result):
        await out_queue.put(result)
        uname_queue.task_done()
        nextuname.set()
        global nprocessed
        nprocessed += 1

    async def putback(job):
        await uname_queue.put(job)
        uname_queue.task_done()

    await asyncio.sleep(workernum * 0.1)
    while True:
        job: UsernameJob = await uname_queue.get()
        try:
            # Get stats for the requested username.
            player: PlayerRecord = await get_player_stats(sess, job.username)
        except UserNotFound:
            await putout(PlayerRecord(rank=job.rank, username=job.username, missing=True))
        except RequestFailed:
            logging.info(f"{name}: caught RequestFailed, raising")
            await putback(job)
            raise
        except asyncio.CancelledError:
            logging.debug(f"{name}: cancelled")
            await putback(job)
            raise
        await putout(player)


async def sort_buffer(in_queue: asyncio.PriorityQueue, out_queue: asyncio.Queue):
    heap = []
    next_rank = None  # rank of item that should be released from the heap next
    while True:
        # Get the next item to be added to the heap.
        in_item: PlayerRecord = await in_queue.get()

        # If heap is full, the item with next_rank was never seen. Consider it, and all
        # items up to the current lowest item on the heap, unaccounted for in sorting.
        while len(heap) >= MAX_HEAPSIZE:
            lowest_item: PlayerRecord = heapq.heappop(heap)
            logging.debug(f"sort buffer: heap overflow, changing next_rank from {next_rank} to {lowest_item.rank}")
            next_rank = lowest_item.rank

        # Add the newly received item to the heap.
        heapq.heappush(heap, in_item)
        if len(heap) == 1:
            logging.debug(f"sort buffer: pushed first item, has rank {heap[0].rank}")
        if next_rank is None:
            next_rank = in_item.rank

        # Release as many items as we can without hitting a gap in ranks.
        nreleased = 0
        i = 0
        while heap and heap[0].rank <= next_rank:
            out_item: PlayerRecord = heapq.heappop(heap)
            if not out_item.missing:
                await out_queue.put(out_item)  # don't export data for players marked as not found
            in_queue.task_done()
            next_rank = max(next_rank, out_item.rank + 1)
            nreleased += 1
            if i == 0:
                firstout = out_item.rank
            lastout = out_item.rank

        if nreleased > MAX_HEAPSIZE // 2:
            logging.debug(f"sort buffer: flushed {nreleased} items (ranks {firstout}-{lastout}, heap size is now {len(heap)})")


async def export_records(in_queue: Queue, coll: AsyncIOMotorCollection):
    async def getbatch() -> List[PlayerRecord]:
        players = []
        while len(players) < 50:
            try:
                next: PlayerRecord = await asyncio.wait_for(in_queue.get(), timeout=0.25)
                players.append(next)
            except asyncio.TimeoutError:
                break
        return players

    async def export(players):
        await coll.insert_many([player_to_mongodoc(p) for p in players])
        for _ in range(len(players)):
            in_queue.task_done()

    while True:
        players = await getbatch()
        if players:
            await export(players)


async def track_progress(remaining: int):
    with tqdm(initial=nprocessed, total=remaining) as pbar:
        while True:
            await asyncio.sleep(0.5)
            pbar.n = nprocessed
            pbar.refresh()


async def detect_finished(page_queue, uname_queue, results_queue, export_queue):
    await page_queue.join()
    await uname_queue.join()
    await results_queue.join()
    await export_queue.join()
    raise DoneScraping


async def stop_tasks(T):
    for task in T:
        task.cancel()
    await asyncio.gather(*T, return_exceptions=True)  # suppress CancelledErrors


async def get_prev_progress(coll: Collection) -> int:
    doc = await coll.find_one({}, sort=[('rank', -1)])
    if doc is None:
        return None
    top_player = mongodoc_to_player(doc)
    return top_player.rank


def build_page_jobqueue(start_rank: int, stop_rank: int) -> PriorityQueue:
    firstpage, startind, lastpage, endind = get_page_range(start_rank, stop_rank)
    global currentpage
    currentpage = firstpage

    queue = asyncio.PriorityQueue()
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(pagenum=pagenum,
                      startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        queue.put_nowait(job)
    return queue


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, loglevel: str = 'warning', usevpn: bool = True, drop: bool = False):

    logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                        datefmt="%H:%M:%S", level=getattr(logging, loglevel.upper()),
                        filename='scrape_hiscores.log', filemode='w')

    connect_mongo(mongo_url)  # check connectivity
    coll = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        logging.info(f"dropped collection '{mongo_coll}'")

    # Start from previous progress, if possible.
    prev_progress = await get_prev_progress(coll)
    if prev_progress and prev_progress >= start_rank:
        logging.warning(f"found an existing record at rank {prev_progress}")
        if prev_progress >= stop_rank:
            logging.warning("nothing to do")
            return
        start_rank = prev_progress + 1
        logging.warning(f"starting from {start_rank}")

    # Build the job queues conjoining each stage of the processing pipeline.
    page_jobqueue = build_page_jobqueue(start_rank, stop_rank)  # page workers get jobs from here
    uname_jobqueue = asyncio.PriorityQueue()  # page workers put usernames here, stats workers get them from here
    results_queue = asyncio.PriorityQueue()   # stats workers put results here, sort buffer gets them from here
    export_queue = asyncio.Queue()            # sort buffer puts sorted results here, they are exported to DB

    nextpage = asyncio.Event()   # signals next page should be enqueued, raised by one page worker for another
    nextuname = asyncio.Event()  # signals next username should be enqueued, raised by stats workers for page worker
    nextpage.set()
    nextuname.set()
    global nprocessed
    nprocessed = 0

    # Spawn the global tasks for sorting, exporting and detecting completion.
    sort = asyncio.create_task(sort_buffer(results_queue, export_queue))  # sort scraped records within fixed queue
    export = asyncio.create_task(export_records(export_queue, coll))      # export scraped records to database
    check_done = asyncio.create_task(                                     # raise signal when all scraping is done
        detect_finished(page_jobqueue, uname_jobqueue, results_queue, export_queue))

    # Get root permissions for VPN management.
    if usevpn:
        pwd = askpass()
        if not pwd:
            usevpn = False

    ntotal = stop_rank - start_rank + 1
    t = Timer(text="done ({minutes:.1f} minutes)")
    t.start()
    async with aiohttp.ClientSession() as sess:

        def start_workers() -> List[asyncio.Task]:
            T = [asyncio.create_task(track_progress(remaining=ntotal - nprocessed))]
            for i in range(N_PAGE_WORKERS):
                T.append(asyncio.create_task(
                    page_worker(sess, page_jobqueue, uname_jobqueue, nextpage, nextuname, workernum=i)))
            for i in range(nworkers):
                T.append(asyncio.create_task(
                    stats_worker(sess, uname_jobqueue, results_queue, nextuname, workernum=i)))
            return T

        logging.info(f"beginning to scrape (start: {start_rank}, stop: {stop_rank}, {nworkers} stats workers)")
        while True:
            if usevpn:
                logging.info(f"resetting VPN...")
                getsudo(pwd)
                reset_vpn()
                logging.info(f"successfully reset VPN")

            # Spawn the data scraping tasks and wait until requests start getting blocked.
            workers = start_workers()
            try:
                await asyncio.gather(*workers, sort, export, check_done)
            except DoneScraping:
                break
            except RequestFailed as e:
                logging.info(f"main: caught RequestFailed: {e}")
                continue
            except Exception as e:
                logging.critical(f"main: caught exception: {e}")
                raise
            finally:
                logging.debug("main: cancelling workers...")
                await stop_tasks(workers)

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
        logging.warning(f"running with >{30 - N_PAGE_WORKERS} stats workers is not recommended. This will "
                        f"create more than 30 open connections at once, exceeding the remote server limit.")

    asyncio.run(main(args.mongo_url, args.mongo_coll, args.start_rank, args.stop_rank,
                     args.num_workers, args.log_level, args.usevpn, args.drop))
