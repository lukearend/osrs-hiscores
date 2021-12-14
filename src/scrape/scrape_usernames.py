#!/usr/bin/env python3

""" Download stats for the top 2 million players on the main OSRS hiscores.
    This scrape can be run repeatedly without destroying previous results.
    Player data is scraped page by page, for each of 80,000 pages containing
    25 players each. Once all pages have been scraped, running this script
    will have no effect.
"""

import asyncio
import os
import pathlib
import pickle
import random
import sys

import aiohttp
from tqdm import tqdm

from src.scrape import (pull_hiscores_page, parse_hiscores_page, pull_player_stats,
                        repeat_shuffled, run_subprocess)


async def page_worker(i, session, job_queue, username_queue, ip_blocked):
    await asyncio.sleep(4 * random.random())
    while not ip_blocked.is_set():
        try:
            page_num = job_queue.get_nowait()
            if page_num == 9e9:
                await username_queue.put((9e9, ''))
                return
        except asyncio.QueueEmpty:
            return

        try:
            raw_html = await pull_hiscores_page(session, page_num)
        except Exception as e:
            print("page worker {}: got blocked: {}".format(i, e))
            job_queue.put_nowait(page_num)
            ip_blocked.set()
            await username_queue.put((9e9, ''))
            return

        try:
            ranks, usernames = parse_hiscores_page(raw_html)
        except Exception as e:
            print("page worker {}: failed parse: {})".format(i, e))
            job_queue.put_nowait(page_num)
            raise e

        for rank, username in zip(ranks, usernames):
            await username_queue.put((rank, username))


async def stats_worker(i, session, username_queue, out_file, file_lock, pbar):
    await asyncio.sleep(4 * random.random())
    with open(out_file, 'a') as f:
        while True:

            rank, username = await username_queue.get()
            if username == '':
                await username_queue.put((9e9, ''))    # Put sentinel back so
                break                                  # others will see it too.

            try:
                player_csv = await pull_player_stats(session, username)

                async with file_lock:
                    f.write(player_csv + '\n')

                pbar.update(1)

            except Exception as e:
                await username_queue.put((rank, username))
                print("stats worker {}: exception: {}".format(i, e))
                break


async def scrape_till_blocklisted(job_queue, out_file, pbar):

    page_workers = 2
    stats_workers = 36

    async with aiohttp.ClientSession() as session:
        tasks = []

        # Download pages in roughly numerical order with parallel workers.

        is_blocked = asyncio.Event()
        username_queue = asyncio.PriorityQueue(maxsize=stats_workers)
        for i in range(page_workers):
            task = asyncio.create_task(
                page_worker(i, session, job_queue, username_queue, is_blocked))
            tasks.append(task)

        # Workers read off the username queue and request
        # CSV stats for each player using the CSV API.

        file_lock = asyncio.Lock()
        for i in range(stats_workers):
            task = asyncio.create_task(
                stats_worker(i, session, username_queue, out_file, file_lock, pbar))
            tasks.append(task)

        await asyncio.gather(*tasks)


async def scrape_data(out_file, start_page=1, end_page=80000):

    # Get VPN locations by parsing the output of `expresso locations`.
    print("getting location codes...", end=' ', flush=True)
    output = await run_subprocess('expresso locations')
    print("done")

    # Parse lines like: "- USA - Chicago (9)" -> 9
    #                   "- India (via UK) (152)" -> 152
    location_codes = []
    use_regions = ['Australia', 'Canada', 'France', 'Germany',
                   'Netherlands', 'Spain', 'UK', 'USA']
    for line in output.split('\n'):
        if any([line.startswith('- ' + region) for region in use_regions]):
            tmp = line.split(')')[-2]
            tmp = tmp.split('(')[-1]
            code = int(tmp)
            location_codes.append(code)

    job_queue = asyncio.PriorityQueue()
    for page_num in range(start_page, end_page + 1):
        job_queue.put_nowait(page_num)

    # Sentinel value for priority queue... big number
    job_queue.put_nowait(9e9)

    # Switch the VPN whenever we start getting blocked from too many requests.

    # for location in repeat_shuffled(location_codes):

    print("resetting vpn connection...", end=' ', flush=True)
    # cmd = 'expresso connect --change --random {}'.format(location)
    cmd = 'expresso connect 149'
    output = await run_subprocess(cmd)
    # print("done (location code {})".format(location))

    pbar = tqdm(total=(end_page - start_page + 1) * 25)

    while True:
        await scrape_till_blocklisted(job_queue, out_file, pbar)
        if job_queue.empty():
            break

    pbar.close()


async def main(out_file):
    print("scraping OSRS hiscores data...")

    if not os.path.isfile(out_file):
        skills_file = pathlib.Path(__file__).resolve().parent.parent.parent / 'reference/skills.csv'
        with open(skills_file, 'r') as f:
            skills = f.read().strip().split('\n')
        with open(out_file, 'w') as f:
            f.write(','.join(skills) + '\n')

    await scrape_data(out_file, start_page=1, end_page=40)
    print("done")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(*sys.argv[1:])
    )
