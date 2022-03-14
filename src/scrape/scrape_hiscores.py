import argparse
import asyncio
import subprocess
from asyncio import PriorityQueue
from dataclasses import dataclass
from pathlib import Path
from typing import List

from codetiming import Timer
from pymongo.collection import Collection


import aiohttp
import motor.motor_asyncio
from tqdm.asyncio import tqdm

from src.common import global_db_name
from src.scrape import get_page_usernames, get_player_stats, player_to_mongodoc, \
    PageRequestFailed, UserRequestFailed, UserNotFound, IPAddressBlocked


class ResetVPN(Exception):
    pass

class DoneScraping(Exception):
    pass


@dataclass(order=True)
class PageJob:
    pagenum: int
    startind: int = 0  # start index of the usernames wanted from this page
    endind: int = 25   # end index of the usernames wanted from this page


async def download_stats(sess, username_jobs: PriorityQueue, out_queue: PriorityQueue):
    while True:
        job = await username_jobs.get()
        try:
            _, username = job
            playerdata = await get_player_stats(sess, username)
        except asyncio.CancelledError:
            username_jobs.put_nowait(job)
            raise
        except (UserRequestFailed, IPAddressBlocked):
            username_jobs.put_nowait(job)
            raise ResetVPN
        except UserNotFound:
            continue
        else:
            await out_queue.put((playerdata.rank, playerdata))


async def export_results(export_jobs: PriorityQueue, mongo_coll: Collection, progress_bar: tqdm):
    while True:
        _, playerdata = await export_jobs.get()
        playerdoc = player_to_mongodoc(playerdata)
        try:
            await mongo_coll.insert_one(playerdoc)
            progress_bar.update(1)
        except asyncio.CancelledError:
            await mongo_coll.insert_one(playerdoc)
            progress_bar.update(1)
            raise


async def download_pages(sess, page_jobs: PriorityQueue, username_buffer: PriorityQueue):
    while True:
        job = await page_jobs.get()
        try:
            while username_buffer.qsize() > 1000:
                await asyncio.sleep(0.1)
            if username_buffer.qsize() < 975:
                await asyncio.sleep(0.25)
            _, page = job
            usernames = await get_page_usernames(sess, page.pagenum)
            usernames = usernames[page.startind:page.endind]
            for username_job in enumerate(usernames):
                username_buffer.put_nowait(username_job)
        except (asyncio.CancelledError, PageRequestFailed, IPAddressBlocked):
            page_jobs.put_nowait(job)
            raise


async def watch_done(page_queue: PriorityQueue, uname_queue: PriorityQueue, out_queue: PriorityQueue):
    while True:
        await asyncio.sleep(2)
        if page_queue.qsize() == 0 and uname_queue.qsize() == 0 and out_queue.qsize() == 0:
            try:
                item = await asyncio.wait_for(out_queue.get(), timeout=2)
            except asyncio.TimeoutError:
                raise DoneScraping
            else:
                await out_queue.put(item)


def get_page_joblist(start_rank: int, end_rank: int) -> List[PageJob]:
    if start_rank > end_rank:
        raise ValueError(f"start rank ({start_rank}) cannot be greater than end rank ({end_rank})")

    first_page = (start_rank - 1) // 25 + 1
    last_page = (end_rank - 1) // 25 + 1
    first_page_startind = (start_rank - 1) % 25
    last_page_endind = (end_rank - 1) % 25 + 1

    jobs = []
    for pagenum in range(first_page, last_page + 1):
        startind = first_page_startind if pagenum == first_page else 0
        endind = last_page_endind if pagenum == last_page else 25
        page = PageJob(pagenum, startind, endind)
        jobs.append(page)
    return jobs


def reset_vpn():
    vpn_script = Path(__file__).resolve().parents[2] / "bin" / "reset_vpn"
    subprocess.run(vpn_script).check_returncode()


async def stop_tasks(tasks):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)  # supresses CancelledErrors


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int, nworkers: int, drop: bool = False):
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    coll = mongo[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    # Make a job queue containing the pages to scrape for usernames.
    page_job_queue = asyncio.PriorityQueue()
    for i, page in enumerate(get_page_joblist(start_rank, stop_rank)):
        page_job_queue.put_nowait((i, page))

    # Make queues for the usernames in line for query and the stat records being exported to database.
    username_job_queue = asyncio.PriorityQueue()
    export_queue = asyncio.PriorityQueue(maxsize=200)

    # reset_vpn()

    t = Timer(text="done ({minutes:.1f} minutes)")
    t.start()
    with tqdm(total=stop_rank - start_rank + 1) as pbar:
        async with aiohttp.ClientSession() as sess:

            def start_tasks() -> List[asyncio.Task]:
                T = [asyncio.create_task(watch_done(page_job_queue, username_job_queue, export_queue))]
                for _ in range(nworkers):
                    T.append(asyncio.create_task(
                        download_stats(sess, username_jobs=username_job_queue, out_queue=export_queue)))
                for _ in range(2):
                    T.append(asyncio.create_task(
                        download_pages(sess, page_jobs=page_job_queue, username_buffer=username_job_queue)))
                for _ in range(1):
                    T.append(asyncio.create_task(
                        export_results(export_jobs=export_queue, mongo_coll=coll, progress_bar=pbar)))
                return T

            while True:
                tasks = start_tasks()
                try:
                    await asyncio.gather(*tasks)
                except ResetVPN:
                    await stop_tasks(tasks)
                    reset_vpn()
                except DoneScraping:
                    await stop_tasks(tasks)
                    break
                except Exception:
                    await stop_tasks(tasks)
                    raise
    t.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Download player data from OSRS hiscores into MongoDB.""")
    parser.add_argument('--mongo-url', required=True, help="store data in Mongo instance running at this URL")
    parser.add_argument('--mongo-coll', required=True, help="put scraped data into this collection")
    parser.add_argument('--start-rank', required=True, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', required=True, type=int, help="stop data collection at this rank")
    parser.add_argument('--num-workers', default=32, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--drop', action='store_true', help="if set, will drop collection before scrape begins")
    args = parser.parse_args()
    asyncio.run(main(args.mongo_url, args.mongo_coll, args.start_rank, args.stop_rank, args.num_workers, args.drop))
