import argparse
import asyncio
import subprocess
from asyncio import PriorityQueue, Lock
from dataclasses import dataclass
from pathlib import Path
from typing import List

from codetiming import Timer
from pymongo.collection import Collection

import aiohttp
import motor.motor_asyncio
from tqdm.asyncio import tqdm

from src.common import global_db_name
from src.scrape import get_page_usernames, get_player_stats, playerrecord_to_mongodoc, \
    RequestFailed, UserNotFound, IPAddressBlocked


UNAME_BUFSIZE = 500


class ResetVPN(Exception):
    pass


class VPNFailure(Exception):
    pass


class DoneScraping(Exception):
    pass


@dataclass(order=True)
class PageJob:
    pagenum: int
    startind: int = 0  # start index of the usernames wanted from this page
    endind: int = 25   # end index of the usernames wanted from this page


async def page_worker(sess, job_queue: PriorityQueue, username_buffer: PriorityQueue, out_lock: Lock, delay: int = 0):
    await asyncio.sleep(delay)
    while True:
        priority, job = await job_queue.get()
        try:
            page_unames = await get_page_usernames(sess, job.pagenum)
            unames = page_unames[job.startind:job.endind]

            await out_lock.acquire()
            while username_buffer.qsize() > UNAME_BUFSIZE - 25:
                await asyncio.sleep(0.1)
            for i, uname in enumerate(unames):
                username_buffer.put_nowait((job.pagenum * 25 + i, uname))
            out_lock.release()

        except Exception:
            job_queue.put_nowait((priority, job))
            raise


async def stats_worker(sess, username_jobs: PriorityQueue, out_queue: PriorityQueue, delay: float):
    await asyncio.sleep(delay)
    while True:
        priority, username = await username_jobs.get()
        try:
            playerdata = await get_player_stats(sess, username)
            await out_queue.put((priority, playerdata))
        except UserNotFound:
            print(f"player with username '{username}' not found, ")
            continue
        except Exception:
            username_jobs.put_nowait((priority, username))
            raise


async def export_results(export_jobs: PriorityQueue, mongo_coll: Collection, progress_bar: tqdm):
    while True:
        await asyncio.sleep(0.25)
        docs = []
        try:
            while True:
                _, playerdata = export_jobs.get_nowait()
                docs.append(playerrecord_to_mongodoc(playerdata))
        except asyncio.QueueEmpty:
            if docs:
                await asyncio.shield(mongo_coll.insert_many(docs))
                progress_bar.update(len(docs))


async def watch_for_done(page_queue: PriorityQueue, uname_queue: PriorityQueue, out_queue: PriorityQueue):
    while True:
        await asyncio.sleep(1)
        if page_queue.qsize() == 0 and uname_queue.qsize() == 0 and out_queue.qsize() == 0:
            try:
                await out_queue.put(await asyncio.wait_for(out_queue.get(), timeout=1))
            except asyncio.TimeoutError:
                raise DoneScraping


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
    try:
        subprocess.run(vpn_script).check_returncode()
    except subprocess.CalledProcessError as e:
        raise VPNFailure(f"failed to reset VPN: {e}")


async def stop_tasks(tasks):
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)  # suppress CancelledErrors


async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int,
               nworkers: int = 28, use_vpn: bool = True, drop: bool = False):
    mongo = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
    coll = mongo[global_db_name()][mongo_coll]
    if drop:
        await coll.drop()
        print(f"dropped collection '{mongo_coll}'")

    top_player = await coll.find_one({}, {'rank': 1}, sort=[('rank', -1)])
    if top_player:
        highest_rank = top_player['rank']
        start_rank = max(highest_rank - 2 * UNAME_BUFSIZE + 1, start_rank)
        print(f"found an existing record at rank {highest_rank}, starting from {start_rank}")

    # Make a job queue containing the pages to scrape for usernames.
    page_job_queue = asyncio.PriorityQueue()
    for i, page in enumerate(get_page_joblist(start_rank, stop_rank)):
        page_job_queue.put_nowait((i, page))

    # Make queues for the usernames in line for query and the stat records being exported to database.
    username_job_queue = asyncio.PriorityQueue()
    export_queue = asyncio.PriorityQueue()

    with tqdm(total=stop_rank - start_rank + 1) as pbar:
        async with aiohttp.ClientSession() as sess:

            def start_workers() -> List[asyncio.Task]:
                T = [
                    asyncio.create_task(export_results(export_queue, mongo_coll=coll, progress_bar=pbar)),
                    asyncio.create_task(watch_for_done(page_job_queue, username_job_queue, export_queue))
                ]
                queue_lock = asyncio.Lock()
                for i in range(2):
                    T.append(asyncio.create_task(
                        page_worker(sess, page_job_queue, username_job_queue, queue_lock, delay=i * 0.25)))
                for i in range(nworkers):
                    T.append(asyncio.create_task(
                        stats_worker(sess, username_job_queue, export_queue, delay=i * 0.1)))
                return T

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
                    await stop_tasks(tasks)
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
