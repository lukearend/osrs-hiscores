import argparse
import asyncio
import heapq
import logging
import time
from asyncio import PriorityQueue, Queue
from typing import List

import aiohttp
import motor.motor_asyncio
from aiohttp import ClientSession
from codetiming import Timer
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.collection import Collection
from tqdm.asyncio import tqdm

from src.common import global_db_name
from src.scrape import UsernameJob, PageJob, PlayerRecord, RequestFailed, UserNotFound, IPAddressBlocked, \
    get_hiscores_page, get_player_stats, get_page_range, reset_vpn, mongodoc_to_player, player_to_mongodoc


N_PAGE_WORKERS = 2
UNAME_BUFSIZE = 100
SORT_BUFSIZE = 1000

uname_qlock = asyncio.Condition()
currentpage = 0
nprocessed = 0


class DoneScraping(Exception):
    """ Raise when all scraping is done to indicate script should exit. """


async def page_worker(sess: ClientSession, page_queue: PriorityQueue, out_queue: PriorityQueue, workernum: int = 0):
    name = f"page worker {workernum}"

    def putback(job):
        job.startind += enqueued
        job.nfailed += 1
        page_queue.put_nowait(job)
        logging.info(f"{name}: put back page {job.pagenum} (startind: {job.startind}, endind: {job.endind})")
        page_queue.task_done()
        logging.info(f"{name}: job {job.pagenum} has now failed {job.nfailed} times")

    await asyncio.sleep(workernum * 0.25)
    global currentpage
    while True:
        job: PageJob = await page_queue.get()
        logging.debug(f"{name}: got page job {job.pagenum} from queue")
        enqueued = 0
        try:
            logging.debug(f"{name}: requesting page {job.pagenum}...")
            t0 = time.time()
            ranks, unames = await get_hiscores_page(sess, job.pagenum)
            logging.debug(f"{name}: got page {job.pagenum} from OSRS hiscores, {time.time() - t0:.2f} sec")

            async with uname_qlock:
                while currentpage != job.pagenum:
                    logging.debug(f"{name}: current page is {currentpage} (I have {job.pagenum}), waiting for my turn...")
                    await uname_qlock.wait()
                for rank, uname in list(zip(ranks, unames))[job.startind:job.endind]:
                    outjob = UsernameJob(rank, uname)
                    await out_queue.put(outjob)
                    logging.debug(f"{name}: enqueued ({outjob.rank}, '{outjob.username}')")
                    enqueued += 1

        except asyncio.CancelledError:
            logging.info(f"{name}: cancelled")
            putback(job)
            raise
        except Exception as e:
            logging.error(f"{name}: caught exception: {e}")
            putback(job)
            logging.error(f"{name}: raising {type(e).__name__}")
            raise

        currentpage += 1
        page_queue.task_done()
        logging.debug(f"{name}: finished page {job.pagenum}")


async def stats_worker(sess: ClientSession, uname_queue: PriorityQueue, out_queue: Queue, workernum: int = 0):
    name = f"stats worker {workernum}"

    def putback(job):
        job.nfailed += 1
        uname_queue.put_nowait(job)
        logging.info(f"{name}: put ({job.rank}, {job.username}) back on username queue...")
        logging.info(f"{name}: job ({job.rank}, {job.username}) has now failed {job.nfailed} times")
        uname_queue.task_done()

    await asyncio.sleep(workernum * 0.1)
    while True:
        job: UsernameJob = await uname_queue.get()
        logging.debug(f"{name}: got ({job.rank}, {job.username}) from queue)")
        try:
            logging.debug(f"{name}: requesting stats for ({job.rank}, '{job.username}')...")
            t0 = time.time()
            player: PlayerRecord = await get_player_stats(sess, job.username)
            logging.debug(f"{name}: got stats for ({job.rank}, '{job.username}'), {time.time() - t0:.2f} sec")
            await out_queue.put(player)
        except UserNotFound:
            print(f"player with username '{job.username}' (rank {job.rank}) not found, skipping")
            logging.warning(f"{name}: player with username '{job.username}' (rank {job.rank}) not found, skipping")

        except asyncio.CancelledError:
            logging.info(f"{name}: cancelled")
            putback(job)
            raise
        except Exception as e:
            logging.error(f"{name}: caught exception: {e}")
            putback(job)
            logging.error(f"{name}: raising {type(e).__name__}")
            raise

        global nprocessed
        nprocessed += 1
        uname_queue.task_done()
        logging.debug(f"{name}: finished ({job.rank}, {job.username})")


async def sort_buffer(in_queue: asyncio.PriorityQueue, out_queue: asyncio.Queue, start_rank: int):
    heap = []
    lastout = start_rank - 1
    while True:
        item = await in_queue.get()
        heapq.heappush(heap, item)
        logging.debug(f"sort buffer: added ({item.rank}, {item.username}) to heap (size {len(heap)}, heap[0] = {heap[0].rank}, lastout = {lastout})")
        while heap[0].rank == lastout + 1:
            out = heapq.heappop(heap)
            logging.debug(f"sort buffer: removed ({out.rank}, {out.username}) from heap (size {len(heap)})")
            await out_queue.put(out)
            lastout = out.rank
            logging.debug(f"sort buffer: placed ({out.rank}, {out.username}) on export queue")
            in_queue.task_done()
            if not heap:
                break


async def export_records(in_queue: Queue, coll: AsyncIOMotorCollection):

    async def getbatch() -> List[PlayerRecord]:
        players = []
        while len(players) < 100:
            try:
                next = await asyncio.wait_for(in_queue.get(), timeout=0.25)
                players.append(next)
            except asyncio.TimeoutError:
                return players

    async def export(players):
        await coll.insert_many([player_to_mongodoc(p) for p in players])
        for _ in range(len(players)):
            in_queue.task_done()
        logging.debug(f"exported {len(players)} documents: (ranks {players[0].rank}-{players[-1].rank})")

    while True:
        players = await getbatch()
        if players:
            await export(players)


async def track_progress(ntotal: int):
    with tqdm(initial=nprocessed, total=ntotal) as pbar:
        while True:
            await asyncio.sleep(0.5)
            pbar.n = nprocessed
            pbar.update()


async def detect_finished(page_queue, uname_queue, results_queue, export_queue):
    await page_queue.join()
    logging.debug("page queue joined")
    await uname_queue.join()
    logging.debug("username queue joined")
    logging.debug(f"nprocessed: {nprocessed}")
    await results_queue.join()
    logging.debug("results queue joined")
    await export_queue.join()
    logging.debug("export queue joined")
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
    global currentpage
    currentpage = firstpage
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(pagenum=pagenum,
                      startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        queue.put_nowait(job)
    return queue


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, use_vpn: bool = True, drop: bool = False):
    logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                        datefmt="%H:%M:%S", level=logging.DEBUG,
                        filename='scrape_hiscores.log', filemode='w')

    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    coll = mongo[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    prev_progress = await get_prev_progress(coll)
    if prev_progress:
        print(f"found an existing record at rank {prev_progress}, ", end='')
        if prev_progress >= stop_rank:
            print("nothing to do")
            return
        elif prev_progress >= start_rank:
            start_rank = prev_progress + 1
            print(f"starting from {start_rank}")

    n_to_process = stop_rank - start_rank + 1
    page_jobqueue = build_page_jobqueue(start_rank, stop_rank)
    uname_jobqueue = asyncio.PriorityQueue()
    results_queue = asyncio.PriorityQueue()
    export_queue = asyncio.Queue()

    asyncio.create_task(sort_buffer(results_queue, export_queue, start_rank))
    asyncio.create_task(export_records(export_queue, coll))
    asyncio.create_task(track_progress(ntotal=n_to_process))
    async with aiohttp.ClientSession() as sess:

        def start_workers() -> List[asyncio.Task]:
            T = [asyncio.create_task(detect_finished(page_jobqueue, uname_jobqueue, results_queue, export_queue))]
            for i in range(N_PAGE_WORKERS):
                T.append(asyncio.create_task(
                    page_worker(sess, page_jobqueue, uname_jobqueue, workernum=i)))
            for i in range(nworkers):
                T.append(asyncio.create_task(
                    stats_worker(sess, uname_jobqueue, results_queue, workernum=i)))
            return T

        async def stop_workers(tasks):
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)  # suppress CancelledErrors

        t = Timer(text="done ({minutes:.1f} minutes)")
        t.start()
        while True:
            if use_vpn:
                reset_vpn()
            tasks = start_workers()
            try:
                await asyncio.gather(*tasks)
            except (RequestFailed, IPAddressBlocked) as e:
                print(e)
                logging.debug(f"main: caught {e}")
                continue
            except DoneScraping:
                break
            except Exception as e:
                logging.debug(f"main: caught {e}")
                raise
            finally:
                logging.debug(f"main: cancelling workers...")
                await stop_workers(tasks)
        t.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Download player data from OSRS hiscores into MongoDB.""")
    parser.add_argument('--mongo-url', required=True, help="store data in Mongo instance running at this URL")
    parser.add_argument('--mongo-coll', required=True, help="put scraped data into this collection")
    parser.add_argument('--start-rank', required=True, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', required=True, type=int, help="stop data collection at this rank")
    parser.add_argument('--num-workers', default=28, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--novpn', dest='usevpn', action='store_false', help="if set, will run without using VPN")
    parser.add_argument('--drop', action='store_true', help="if set, will drop collection before scrape begins")
    args = parser.parse_args()
    asyncio.run(main(args.mongo_url, args.mongo_coll, args.start_rank, args.stop_rank,
                     args.num_workers, args.usevpn, args.drop))
