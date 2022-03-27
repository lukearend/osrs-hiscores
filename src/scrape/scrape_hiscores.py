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
from src.scrape import UsernameJob, PageJob, PlayerRecord, RequestFailed, UserNotFound, IPAddressBlocked, \
    get_hiscores_page, get_player_stats, get_page_range, reset_vpn, mongodoc_to_player, player_to_mongodoc, getsudo, \
    askpass

N_PAGE_WORKERS = 2   # number of page workers downloading rank/username info
UNAME_BUFSIZE = 50   # maximum length of buffer containing username jobs for stats workers
MAX_HEAPSIZE = 1000  # maximum size for the sorting heap before it allows records to be skipped

currentpage = 0
nprocessed = 0


async def page_worker(sess: ClientSession, page_queue: PriorityQueue, out_queue: PriorityQueue,
                      nextpage: Event, nextuname: Event, workernum: int = 0):
    name = f"page worker {workernum}"

    async def putback(job, unames_done=0):
        job.startind += unames_done
        job.nfailed += 1
        await page_queue.put(job)
        page_queue.task_done()

    await asyncio.sleep(workernum * 0.25)
    global currentpage
    while True:
        job: PageJob = await page_queue.get()
        n_enqueued = 0
        try:
            ranks, unames = await get_hiscores_page(sess, job.pagenum)

            while currentpage != job.pagenum:
                await nextpage.wait()
                nextpage.clear()

            for rank, uname in list(zip(ranks, unames))[job.startind:job.endind]:
                outjob = UsernameJob(rank, uname)
                while out_queue.qsize() >= UNAME_BUFSIZE:
                    await nextuname.wait()
                    nextuname.clear()
                await out_queue.put(outjob)
                n_enqueued += 1

            currentpage += 1
            page_queue.task_done()
            nextpage.set()

        except asyncio.CancelledError:
            logging.info(f"{name}: cancelled")
            await putback(job, unames_done=n_enqueued)
            raise

        except Exception as e:
            logging.error(f"{name}: caught exception: {e}")
            await putback(job)
            logging.error(f"{name}: raising {type(e).__name__}")
            raise


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
        logging.info(f"{name}: put ({job.rank}, {job.username}) back on username queue...")
        logging.info(f"{name}: job ({job.rank}, {job.username}) has now failed {job.nfailed} times")

    await asyncio.sleep(workernum * 0.1)
    while True:
        job: UsernameJob = await uname_queue.get()
        try:
            player: PlayerRecord = await get_player_stats(sess, job.username)
            await putout(player)

        except UserNotFound:
            await putout(PlayerRecord(rank=job.rank, username=job.username, missing=True))

        except asyncio.CancelledError:
            logging.info(f"{name}: cancelled")
            await putback(job)
            raise

        except Exception as e:
            logging.error(f"{name}: caught exception: {e}")
            job.nfailed += 1
            if job.nfailed == 3:
                msg = f"{name}: job ({job.rank}, {job.username}) failed too many times, skipping"
                print(msg)
                logging.warning(msg)
                await putout(PlayerRecord(rank=job.rank, username=job.username, missing=True))
            else:
                await putback(job)
                logging.error(f"{name}: raising {type(e).__name__}")
                raise


async def sort_buffer(in_queue: asyncio.PriorityQueue, out_queue: asyncio.Queue, start_rank: int):

    heap = []
    out_rank = start_rank  # rank of item that should be released from the heap next
    while True:
        item = await in_queue.get()
        heapq.heappush(heap, item)

        # If heap is full, skip some records to catch up out_rank with min item on heap.
        if len(heap) > MAX_HEAPSIZE:
            prev = out_rank
            out_rank = heap[0].rank
            if out_rank - prev == 1:
                logging.debug(f"sort buffer: skipped players {prev} through {out_rank - 1} (heap size is {len(heap)})")

            while out_rank < heap[0].rank:
                await out_queue.put(PlayerRecord(rank=out_rank, username=None, missing=True))
                out_rank += 1

        # Release as many items from the heap as we can without hitting a gap in ranks.
        while heap and heap[0].rank == out_rank:
            out = heapq.heappop(heap)
            await out_queue.put(out)
            in_queue.task_done()
            out_rank += 1


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


class DoneScraping(Exception):
    """ Raised when all scraping is done to indicate script should exit. """


async def track_progress(ntotal: int):
    with tqdm(total=ntotal) as pbar:
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


async def get_prev_progress(coll: Collection) -> int:
    doc = await coll.find_one({}, sort=[('rank', -1)])
    if doc is None:
        return None
    top_player = mongodoc_to_player(doc)
    return top_player.rank


def build_page_jobqueue(start_rank: int, stop_rank: int) -> PriorityQueue:
    queue = asyncio.PriorityQueue()
    firstpage, startind, lastpage, endind = get_page_range(start_rank, stop_rank)
    global currentpage, nprocessed
    currentpage = firstpage
    nprocessed = 0
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(pagenum=pagenum,
                      startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        queue.put_nowait(job)
    return queue


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               n_stats_workers: int = 28, use_vpn: bool = True, drop: bool = False):
    logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                        datefmt="%H:%M:%S", level=logging.DEBUG,
                        filename='scrape_hiscores.log', filemode='w')

    connect_mongo(mongo_url)  # check connectivity before acquiring async client
    coll = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    # Start from previous progress, if possible.
    prev_progress = await get_prev_progress(coll)
    if prev_progress and prev_progress >= start_rank:
        print(f"found an existing record at rank {prev_progress}, ", end='')
        if prev_progress >= stop_rank:
            print("nothing to do")
            return
        start_rank = prev_progress + 1
        print(f"starting from {start_rank}")

    # Get root permissions for VPN management.
    if use_vpn:
        pwd = askpass()
        if pwd:
            getsudo(pwd)
        else:
            use_vpn = False

    page_jobqueue = build_page_jobqueue(start_rank, stop_rank)  # page workers get jobs from here
    uname_jobqueue = asyncio.PriorityQueue()  # page workers put usernames here, stats workers get them from here
    results_queue = asyncio.PriorityQueue()   # stats workers put results here, sort buffer gets them from here
    export_queue = asyncio.Queue()            # sort buffer puts sorted results here, they are exported to DB

    nextpage = asyncio.Event()   # signals next page should be enqueued, raised by one page worker for another
    nextuname = asyncio.Event()  # signals next username should be enqueued, raised by stats workers for page worker
    nextpage.set()
    nextuname.set()

    sort = asyncio.create_task(sort_buffer(results_queue, export_queue, start_rank))
    export = asyncio.create_task(export_records(export_queue, coll))
    pbar = asyncio.create_task(track_progress(ntotal=stop_rank - start_rank + 1))
    is_done = asyncio.create_task(detect_finished(page_jobqueue, uname_jobqueue, results_queue, export_queue))
    async with aiohttp.ClientSession() as sess:

        def start_workers() -> List[asyncio.Task]:
            T = []
            for i in range(2):
                T.append(asyncio.create_task(
                    page_worker(sess, page_jobqueue, uname_jobqueue, nextpage, nextuname, workernum=i)))
            for i in range(n_stats_workers):
                T.append(asyncio.create_task(
                    stats_worker(sess, uname_jobqueue, results_queue, nextuname, workernum=i)))
            return T

        async def stop_tasks(T):
            for task in T:
                task.cancel()
            await asyncio.gather(*T, return_exceptions=True)  # suppress CancelledErrors

        t = Timer(text="done ({minutes:.1f} minutes)")
        t.start()
        while True:
            if use_vpn:
                getsudo(pwd)
                reset_vpn()
            workers = start_workers()
            try:
                await asyncio.gather(*workers, sort, export, pbar, is_done)
            except (RequestFailed, IPAddressBlocked) as e:
                print(e)
                logging.debug(f"main: caught {e}")
                continue
            except DoneScraping:
                logging.info("main: caught DoneScraping")
                break
            except Exception as e:
                logging.debug(f"main: caught {e}")
                raise
            finally:
                logging.debug("main: cancelling workers...")
                await stop_tasks(workers)
        t.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Download player data from OSRS hiscores into MongoDB.""")
    parser.add_argument('--mongo-url', default="localhost:27017", help="store data in Mongo instance at this URL")
    parser.add_argument('--mongo-coll', default="scrape", help="put scraped data into this collection")
    parser.add_argument('--start-rank', default=1, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', default=2000000, type=int, help="stop data collection at this rank")
    parser.add_argument('--num-workers', default=28, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--novpn', dest='usevpn', action='store_false', help="if set, will run without using VPN")
    parser.add_argument('--drop', action='store_true', help="if set, will drop collection before scrape begins")
    args = parser.parse_args()

    if args.num_workers + N_PAGE_WORKERS > 30:
        print(f"warning: running with >{30 - N_PAGE_WORKERS} stats workers is not recommended, as this "
              f"will create more than 30 open connections at once, exceeding the remote server limit.")

    asyncio.run(main(args.mongo_url, args.mongo_coll, args.start_rank, args.stop_rank,
                     args.num_workers, args.usevpn, args.drop))
