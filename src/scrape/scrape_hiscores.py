import argparse
import asyncio
import heapq
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
    while True:
        job: PageJob = await page_queue.get()
        try:
            ranks, unames = await get_hiscores_page(sess, job.pagenum)
            ranks = ranks[job.startind:job.endind]
            unames = unames[job.startind:job.endind]
            uname_jobs = [UsernameJob(rank=r, username=u) for r, u in zip(ranks, unames)]
            # todo: find a more robust way to manage these. they need to go in order, and to respect the queue lock.
            # it might be best to switch to using a shared lock, a fixed size queue, and blocking puts instead.
            global currentpage
            while currentpage < job.pagenum:
                await asyncio.sleep(0.25)
            for outjob in uname_jobs:
                out_queue.put_nowait(outjob)
            currentpage += 1
        except Exception:
            page_queue.put_nowait(job)
            raise


async def stats_worker(sess: ClientSession, uname_queue: PriorityQueue, out_queue: Queue, delay: float = 0):
    """ Given a player's username, fetch their stats from the OSRS hiscores.

    :params sess: aiohttp client session
    :params uname_queue: get player username jobs from this queue
    :params out_queue: place processed results on this queue
    """
    await asyncio.sleep(delay)
    while True:
        job: UsernameJob = await uname_queue.get()
        try:
            player: PlayerRecord = await get_player_stats(sess, job.username)
            await out_queue.put(player)
        except UserNotFound:
            print(f"player with username '{job.username}' (rank {job.rank}) not found, skipping")
        except Exception:
            uname_queue.put_nowait(job)
            raise
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
    while True:
        in_item: PlayerRecord = await in_queue.get()
        if len(heap) < SORT_BUFSIZE:
            heapq.heappush(heap, in_item)
        else:
            out_item = heapq.heappushpop(heap, in_item)
            await out_queue.put(out_item)
        if nprocessed >= ntotal:
            for item in heap:
                out_queue.put_nowait(item)
            break


async def export_records(in_queue: Queue, coll: AsyncIOMotorCollection):
    """ Batch export records to database.

    :param in_queue: read records from this queue
    :param coll: export documents to this collection in batches
    """
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
            docs = [player_to_mongodoc(p) for p in batch]
            await coll.insert_many(docs)


async def track_progress(ntotal: int):
    """ Show a progress bar and detect when scraping is complete.

    :param ntotal: total number of player documents expected to be collected
    """
    with tqdm(initial=nprocessed, total=ntotal) as pbar:
        pbar_last = nprocessed
        while True:
            await asyncio.sleep(0.5)
            pbar.update(nprocessed - pbar_last)
            pbar_last = nprocessed
            if nprocessed >= ntotal:
                await asyncio.sleep(2)  # give some time for export queue to flush remaining records
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
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(pagenum=pagenum,
                      startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        queue.put_nowait(job)
    global currentpage
    currentpage = firstpage
    return queue


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, use_vpn: bool = True, drop: bool = False):
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
            T = [asyncio.create_task(track_progress(ntotal=n_to_process))]
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
