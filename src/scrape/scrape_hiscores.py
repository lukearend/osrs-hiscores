import argparse
import asyncio
import heapq
import logging
from asyncio import PriorityQueue, Queue
from dataclasses import dataclass
from typing import List, Any, Tuple

from aiohttp import ClientSession
from codetiming import Timer

import aiohttp
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorCollection
from tqdm.asyncio import tqdm

from src.common import global_db_name
from src.scrape import get_hiscores_page, get_player_stats, player_to_mongodoc, RequestFailed, UserNotFound, \
    IPAddressBlocked, get_page_range, reset_vpn, mongodoc_to_player, player_to_mongodoc, PlayerRecord, UsernameJob, \
    PageJob

N_PAGE_WORKERS = 2
UNAME_BUFSIZE = 100
SORT_BUFSIZE = 1000

currentpage = None          # global var for page currently being enqueued


class SortingError(RuntimeError):
    pass


class DoneScraping(Exception):
    pass


@dataclass
class PageCounter:
    currentpage: int = 0


async def page_worker(sess: ClientSession, pc: PageCounter, job_queue: PriorityQueue,
                      out_buffer: PriorityQueue, delay: int = 0):
    await asyncio.sleep(delay)


async def stats_worker(sess, username_jobs: PriorityQueue, out_buffer: PriorityQueue, delay: float):
    await asyncio.sleep(delay)


async def sort_results(in_queue: PriorityQueue, out_queue: Queue):
    def raise_error(in_rank, out_rank, last_out_rank, heap):
        bufdump = ""
        for i in range(SORT_BUFSIZE):
            player = heapq.heappop(heap)
            bufdump += f"{i}: rank {player.rank}\n"
        raise SortingError(
            f"Rank {out_rank} was about to exit the sort buffer, but the previous item "
            f"that exited was rank {last_out_rank}. Since the scrape workers are currently "
            f"around rank {in_rank}, it's likely rank {last_out_rank + 1} was missed."
            f"Sort buffer:\n{bufdump}")

async def export_results(export_jobs: PriorityQueue, mongo_coll: Collection, start_rank: tqdm, done_rank: int):
    with tqdm(total=done_rank - start_rank + 1) as pbar:
        await asyncio.sleep(0.25)


#####


async def process_page_fn(sess: ClientSession, pc: PageCounter, page_queue: PriorityQueue, out_queue: PriorityQueue):
    job: PageJob = await page_queue.get()
    try:
        ranks, unames = await get_hiscores_page(sess, job.pagenum)
        ranks = ranks[job.startind:job.endind]
        unames = unames[job.startind:job.endind]
        uname_jobs = [UsernameJob(rank=r, username=u) for r, u in zip(ranks, unames)]
        while pc.currentpage < job.pagenum:
            await asyncio.sleep(0.25)
        for outjob in uname_jobs:
            out_queue.put_nowait(outjob)
        pc.currentpage += 1
    except Exception:
        page_queue.put_nowait(job)
        raise


async def process_username_fn(uname_queue: PriorityQueue, out_queue: PriorityQueue, sess: ClientSession):
    job: UsernameJob = await uname_queue.get()
    try:
        player: PlayerRecord = await get_player_stats(sess, job.username)
        await out_queue.put(player)
    except UserNotFound:
        logging.info(f"player with username '{job.username}' not found, skipping")
    except Exception:
        uname_queue.put_nowait(job)
        raise


async def export_fn(in_queue: Queue, coll: AsyncIOMotorCollection, pbar: tqdm, donerank: int):
    batch = []
    while True:
        try:
            batch.append(in_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    if batch:
        docs = [player_to_mongodoc(p) for p in batch]
        await coll.insert_many(docs)
        pbar.update(len(docs))

        if batch[-1].rank == donerank:
            raise DoneScraping


async def sort_buffer(in_queue: asyncio.Queue, out_queue: asyncio.Queue, bufsize: int):
    heap = []
    while True:
        in_item = await in_queue.get()
        if len(heap) < bufsize:
            heapq.heappush(in_item)
        else:
            out_item = heapq.heappushpop(in_item)
            await out_queue.put(out_item)


async def get_prev_progress(coll: Collection) -> int:
    doc = await coll.find_one({}, {'rank': 1}, sort=[('rank', -1)])
    if doc is None:
        return None
    top_player = mongodoc_to_player(doc)
    return top_player.rank


def build_page_jobqueue(start_rank: int, stop_rank: int) -> Tuple[int, PriorityQueue]:
    queue = asyncio.PriorityQueue()
    firstpage, startind, lastpage, endind = get_page_range(start_rank, stop_rank)
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        queue.put_nowait((pagenum, job))
    return firstpage, queue


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, use_vpn: bool = True, drop: bool = False):
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    coll = mongo[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    prev_progress = get_prev_progress(coll)
    if prev_progress and prev_progress >= start_rank:
        start_rank = prev_progress + 1
        print(f"found an existing record at rank {prev_progress}, starting from {start_rank}")

    firstpage, page_jobqueue = build_page_jobqueue(start_rank, stop_rank)
    uname_jobqueue = asyncio.PriorityQueue()
    results_queue = asyncio.PriorityQueue()
    export_queue = asyncio.PriorityQueue()
    pc = PageCounter(currentpage=firstpage)

    asyncio.create_task(sort_buffer(uname_jobqueue, export_queue, bufsize=UNAME_BUFSIZE))
    asyncio.create_task(sort_buffer(export_queue,
    async with aiohttp.ClientSession() as sess:

        def start_workers() -> List[asyncio.Task]:
            T = [asyncio.create_task(export_results(export_queue, coll, start_rank, stop_rank))]
            for i in range(N_PAGE_WORKERS):
                T.append(asyncio.create_task(
                    page_worker(sess, pc, page_jobqueue, uname_jobqueue, delay=i * 0.25)))
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
