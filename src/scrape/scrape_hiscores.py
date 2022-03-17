import argparse
import asyncio
import heapq
from asyncio import PriorityQueue, Queue
from dataclasses import dataclass
from typing import List, Any

from aiohttp import ClientSession
from codetiming import Timer
from pymongo.collection import Collection

import aiohttp
import motor.motor_asyncio
from tqdm.asyncio import tqdm

from src.common import global_db_name
from src.scrape import get_page_usernames, get_player_stats, playerrecord_to_mongodoc, \
    RequestFailed, UserNotFound, IPAddressBlocked, get_page_range, reset_vpn

N_PAGE_WORKERS = 4
UNAME_BUFSIZE = 100
SORT_BUFSIZE = 1000


class SortingError(RuntimeError):
    pass


class DoneScraping(Exception):
    pass


@dataclass(order=True)
class PageJob:
    startind: int = 0  # start index of the usernames wanted from this page
    endind: int = 25   # end index of the usernames wanted from this page


class PageCounter:     # used by page workers to enqueue pages in the correct order
    bufferlock = asyncio.Lock()
    pagefinished = asyncio.Event()
    currentpage = 0


async def page_worker(sess: ClientSession, pc: PageCounter, job_queue: PriorityQueue,
                      out_buffer: PriorityQueue, delay: int = 0):
    await asyncio.sleep(delay)
    while True:
        pagenum, job = await job_queue.get()
        page_start_rank = (pagenum - 1) * 25 + 1
        ranks = [page_start_rank + i for i in range(job.startind, job.endind)]
        try:
            # download and parse the assigned page
            page_unames = await get_page_usernames(sess, pagenum)
            unames = page_unames[job.startind:job.endind]

            # start todo:
            # wait until it is my turn, then enqueue my page
            while pc.currentpage < pagenum:
                await pc.pagefinished.wait()

            pc.pagefinished.clear()
            async with pc.bufferlock:
                for rank, uname in zip(ranks, unames):
                    await out_buffer.put((rank, uname))
            pc.currentpage = pagenum + 1
            pc.pagefinished.set()
            # end todo

        except Exception:
            job_queue.put_nowait((pagenum, job))
            raise


async def stats_worker(sess, username_jobs: PriorityQueue, out_buffer: PriorityQueue, delay: float):
    await asyncio.sleep(delay)
    while True:
        rank, username = await username_jobs.get()
        try:
            playerdata = await get_player_stats(sess, username)
            await out_buffer.put((playerdata.rank, playerdata))
        except UserNotFound:
            print(f"player with username '{username}' not found")
            continue
        except Exception:
            username_jobs.put_nowait((rank, username))
            raise


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

    assert SORT_BUFSIZE > 0
    heap = []

    print("buffering results to be sorted...")
    for _ in tqdm(range(SORT_BUFSIZE)):
        _, player = await in_queue.get()
        heapq.heappush(heap, player)
        print(f"LA: {player.rank}")

    print("exporting results...")
    last_out_rank = player.rank
    while True:
        _, in_player = await in_queue.get()
        out_player = heapq.heappushpop(heap, in_player)
        if out_player.rank != last_out_rank + 1:
            raise_error(in_player.rank, out_player.rank, last_out_rank, heap)
        await out_queue.put(out_player)
        last_out_rank = out_player.rank
        print(f"LA: {in_player.rank}, {out_player.rank}")


async def export_results(export_jobs: PriorityQueue, mongo_coll: Collection, start_rank: tqdm, done_rank: int):

    def flush_queue() -> List[Any]:
        docs = []
        while True:
            try:
                playerdata = export_jobs.get_nowait()
                docs.append(playerrecord_to_mongodoc(playerdata))
            except asyncio.QueueEmpty:
                return docs

    with tqdm(total=done_rank - start_rank + 1) as pbar:
        await asyncio.sleep(0.25)
        docs = flush_queue()
        if docs:
            await mongo_coll.insert_many(docs)
            pbar.update(len(docs))
            if docs[-1]['rank'] == done_rank:
                raise DoneScraping


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, use_vpn: bool = True, drop: bool = False):
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    coll = mongo[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    # Resume from any existing progress.
    existing_top_player = await coll.find_one({}, {'rank': 1}, sort=[('rank', -1)])
    if existing_top_player:
        start_rank = existing_top_player['rank'] + 1
        print(f"found an existing record at rank {existing_top_player['rank']}, starting from {start_rank}")

    # Make a job queue containing the pages to scrape.
    page_job_queue = asyncio.PriorityQueue()
    firstpage, startind, lastpage, endind = get_page_range(start_rank, stop_rank)
    for pagenum in range(firstpage, lastpage + 1):
        job = PageJob(startind=startind if pagenum == firstpage else 0,
                      endind=endind if pagenum == lastpage else 25)
        page_job_queue.put_nowait((pagenum, job))

    page_counter = PageCounter()
    page_counter.currentpage = firstpage

    # Make queues for querying usernames, sorting by rank and exporting results to database.
    username_job_queue = asyncio.PriorityQueue(maxsize=UNAME_BUFSIZE)
    results_buffer = asyncio.Queue(maxsize=SORT_BUFSIZE)
    export_queue = asyncio.Queue()
    asyncio.create_task(sort_results(results_buffer, export_queue))

    async with aiohttp.ClientSession() as sess:

        def start_workers() -> List[asyncio.Task]:
            T = [asyncio.create_task(export_results(export_queue, coll, start_rank, stop_rank))]
            for i in range(N_PAGE_WORKERS):
                T.append(asyncio.create_task(
                    page_worker(sess, page_counter, page_job_queue, username_job_queue, delay=i * 0.25)))
            for i in range(nworkers):
                T.append(asyncio.create_task(
                    stats_worker(sess, username_job_queue, results_buffer, delay=i * 0.1)))
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
