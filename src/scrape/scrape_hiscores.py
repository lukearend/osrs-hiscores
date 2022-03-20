import argparse
import asyncio
import heapq
import logging
import sys
import time
from asyncio import PriorityQueue, Queue
from itertools import count
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

currentpage = 0
nprocessed = 0


class DoneScraping(Exception):
    pass


async def page_worker(sess: ClientSession, page_queue: PriorityQueue, out_queue: PriorityQueue, delay: float = 0):
    """ Fetch an OSRS hiscores page and parse out the 25 rank/username pairs.

    :param sess: aiohttp client session
    :param page_queue: get page jobs from this queue
    :param out_queue: place usernames (as username jobs) on this queue
    """
    await asyncio.sleep(delay)
    workernum = int(delay / 0.25)  # LA: debug
    while True:
        global currentpage
        job: PageJob = await page_queue.get()
        logging.debug(f"page worker {workernum}: got page {job.pagenum} (ranks {(job.pagenum - 1) * 25 + 1}-{job.pagenum * 25}) from page queue)")
        try:
            ranks, unames = await get_hiscores_page(sess, job.pagenum)
            ranks = ranks[job.startind:job.endind]
            unames = unames[job.startind:job.endind]
            uname_jobs = [UsernameJob(rank=r, username=u) for r, u in zip(ranks, unames)]
            # todo: find a more robust way to manage these. they need to go in order, and to respect the queue lock.
            # it might be best to switch to using a shared lock, a fixed size queue, and blocking puts instead.
            while currentpage < job.pagenum:
                await asyncio.sleep(0.25)
            for outjob in uname_jobs:
                out_queue.put_nowait(outjob)
            logging.debug(f"page worker {workernum}: enqueued page {job.pagenum} (ranks {(job.pagenum - 1) * 25 + 1}-{job.pagenum * 25})")
        except asyncio.CancelledError:
            job.nfailed += 1
            page_queue.put_nowait(job)
            page_queue.task_done()
            logging.debug(f"page worker {workernum}: cancelled, put page job {job.pagenum} back on page queue")
            logging.debug(f"job has now failed {job.nfailed} time{'s' if job.nfailed > 1 else ''}")
            raise
        except Exception as e:
            job.nfailed += 1
            page_queue.put_nowait(job)
            page_queue.task_done()
            logging.debug(f"page worker {workernum}: cancelled, put page job {job.pagenum} back on page queue")
            logging.debug(f"job has now failed {job.nfailed} time{'s' if job.nfailed > 1 else ''}")
            raise
        page_queue.task_done()
        logging.debug(f"page worker {workernum}: finished page {job.pagenum}")
        currentpage += 1


async def stats_worker(sess: ClientSession, uname_queue: PriorityQueue, out_queue: Queue, delay: float = 0):
    """ Given a player's username, fetch their stats from the OSRS hiscores.

    :params sess: aiohttp client session
    :params uname_queue: get player username jobs from this queue
    :params out_queue: place processed results on this queue
    """
    await asyncio.sleep(delay)
    workernum = int(delay / 0.1)  # LA: debug
    while True:
        job: UsernameJob = await uname_queue.get()
        logging.debug(f"stats worker {workernum}: got ({job.rank}, {job.username}) from uname_queue)")
        try:
            t0 = time.time()  # LA: debug
            player: PlayerRecord = await get_player_stats(sess, job.username)
            if (dt := time.time() - t0) > 1:
                logging.debug(f"stats worker {workernum}: stats request took {dt} sec")
            await out_queue.put(player)
        except UserNotFound:
            print(f"player with username '{job.username}' (rank {job.rank}) not found, skipping")
        except asyncio.CancelledError:
            job.nfailed += 1
            uname_queue.task_done()
            uname_queue.put_nowait(job)
            logging.debug(f"stats worker {workernum}: cancelled, put ({job.rank}, {job.username}) back on username queue...")
            logging.debug(f"job has now failed {job.nfailed} time{'s' if job.nfailed > 1 else ''}")
            raise
        except Exception as e:
            job.nfailed += 1
            uname_queue.task_done()
            uname_queue.put_nowait(job)
            logging.debug(f"stats worker {workernum}: exception: {e}, put ({job.rank}, {job.username}) back on username queue...")
            logging.debug(f"job has now failed {job.nfailed} time{'s' if job.nfailed > 1 else ''}")
            raise

        uname_queue.task_done()
        logging.debug(f"stats worker {workernum}: finished ({job.rank}, {job.username})")
        global nprocessed
        nprocessed += 1


async def sort_buffer(in_queue: asyncio.PriorityQueue, out_queue: asyncio.Queue, ntotal: int):
    """ Sort records using a fixed-size heap.

    :param in_queue: read records from this queue
    :param out_queue: place sorted records into this queue
    :ntotal: total number of items expected to pass through this buffer,
             the buffer is flushed once this many items have been received
    """
    heap = []
    lastout = None  # LA: debug
    while True:
        in_item: PlayerRecord = await in_queue.get()
        if len(heap) < SORT_BUFSIZE:
            heapq.heappush(heap, in_item)
        else:
            out_item = heapq.heappushpop(heap, in_item)
            # if lastout and lastout.rank != out_item.rank - 1:  # LA: debug - dump queues
            #     while True:
            #         try:
            #             r: PlayerRecord = out_queue.get_nowait()
            #             print(r.rank, r.username)
            #         except asyncio.QueueEmpty:
            #             break
            #     while len(heap) > 0:
            #         r: PlayerRecord = heapq.heappop(heap)
            #         print(r.rank, r.username)
            #     while True:
            #         try:
            #             r: PlayerRecord = in_queue.get_nowait()
            #             print(r.rank, r.username)
            #         except asyncio.QueueEmpty:
            #             break
            #     await asyncio.sleep(1)
            #     print(f"skipped a record. out_item rank: {out_item.rank}, last out_item rank: {lastout.rank}")
            #     sys.exit(1)
            await out_queue.put(out_item)
            in_queue.task_done()
            lastout = out_item  # LA: debug
        if nprocessed >= ntotal:
            for item in heap:
                out_queue.put_nowait(item)
                in_queue.task_done()
            break


async def export_records(in_queue: Queue, coll: AsyncIOMotorCollection):
    """ Batch export records to database.

    :param in_queue: read records from this queue
    :param coll: export documents to this collection in batches
    """
    last_batch_last = None
    while True:
        await asyncio.sleep(0.25)
        batch = []
        while True:
            try:
                nextrecord: PlayerRecord = in_queue.get_nowait()
                batch.append(nextrecord)
            except asyncio.QueueEmpty:
                break
        if batch:
            if last_batch_last:  # LA: debug
                assert last_batch_last == batch[0].rank - 1
            last_batch_last = batch[-1].rank
            docs = [player_to_mongodoc(p) for p in batch]
            await coll.insert_many(docs)
            for _ in range(len(docs)):
                in_queue.task_done()
            logging.debug(f"exported {len(docs)} documents: (ranks {batch[0].rank}-{batch[-1].rank})")  # LA: debug


async def track_progress(ntotal: int):
    with tqdm(initial=nprocessed, total=ntotal) as pbar:
        while True:
            await asyncio.sleep(0.5)
            pbar.n = nprocessed
            pbar.update()


async def detect_finished(page_queue, uname_queue, results_queue, export_queue):
    await page_queue.join()
    await uname_queue.join()
    await results_queue.join()
    await export_queue.join()
    raise DoneScraping


async def get_prev_progress(coll: Collection) -> int:
    """ Detect previous progress by finding the highest-ranked existing document.

    :param coll: search in this collection
    """
    doc = await coll.find_one({}, sort=[('rank', -1)])
    if doc is None:
        return None
    top_player = mongodoc_to_player(doc)
    return top_player.rank


def build_page_jobqueue(start_rank: int, stop_rank: int) -> PriorityQueue:
    """ Build a queue of jobs representing pages to be queried.

    :param start_rank: start data collection from this rank
    :param stop_rank: stop data collection at this rank
    """
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
                        datefmt="%H:%M:%S", level=logging.DEBUG)

    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    coll = mongo[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    prev_progress = await get_prev_progress(coll)
    if prev_progress:
        if prev_progress >= stop_rank:
            print(f"found an existing record at rank {prev_progress}, nothing to do")
            return
        elif prev_progress >= start_rank:
            start_rank = prev_progress + 1
            print(f"found an existing record at rank {prev_progress}, starting from {start_rank}")

    n_to_process = stop_rank - start_rank + 1
    page_jobqueue = build_page_jobqueue(start_rank, stop_rank)
    uname_jobqueue = asyncio.PriorityQueue()
    results_queue = asyncio.PriorityQueue()
    export_queue = asyncio.Queue()

    asyncio.create_task(sort_buffer(results_queue, export_queue, ntotal=n_to_process))
    asyncio.create_task(export_records(export_queue, coll))
    async with aiohttp.ClientSession() as sess:

        def start_workers() -> List[asyncio.Task]:
            T = [asyncio.create_task(track_progress(ntotal=n_to_process)),
                 asyncio.create_task(detect_finished(page_jobqueue, uname_jobqueue, results_queue, export_queue))]
            for i in range(N_PAGE_WORKERS):
                T.append(asyncio.create_task(
                    page_worker(sess, page_jobqueue, uname_jobqueue, delay=i * 0.25)))
            for i in range(nworkers):
                T.append(asyncio.create_task(
                    stats_worker(sess, uname_jobqueue, results_queue, delay=i * 0.1)))
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
                continue
            except DoneScraping:
                break
            finally:
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
