#!/usr/bin/env python3

""" Download stats for the top 2 million players on the main OSRS hiscores.
    This script can be run repeatedly without destroying previous results.
    Player data is scraped page by page, for each of 80,000 pages containing
    25 players each. Once all pages have been scraped, running the script
    will have no effect.
"""

import asyncio
import csv
import os
import pathlib
import pickle
import random
import sys
from collections import defaultdict

import aiohttp
from tqdm import tqdm

from src.scrape import ApiError
from src.scrape import (pull_hiscores_page, parse_hiscores_page, pull_player_stats, run_subprocess,
                        repeat_shuffled)


async def page_worker(name, session, job_queue, page_queue):
    while True:
        try:
            page_num = job_queue.get_nowait()
        except asyncio.QueueEmpty:
            return

        if page_num == float('inf'):
            await page_queue.put((float('inf'), (None, None)))
            return

        try:
            raw_html = await pull_hiscores_page(session, page_num)
            ranks, usernames = parse_hiscores_page(raw_html)
            while page_queue.qsize() >= 4:
                await asyncio.sleep(0.1)
            await page_queue.put((page_num, (ranks, usernames)))

        except Exception:
            job_queue.put_nowait(page_num)
            raise


async def unzip_pages(page_queue, username_queue, bufsize=100):
    while True:
        while username_queue.qsize() >= bufsize - 25:
            await asyncio.sleep(0.1)    # Give player workers some time to process usernames

        page_num, (ranks, usernames) = await page_queue.get()
        if page_num == float('inf'):
            await username_queue.put((float('inf'), None))
            return

        for rank, username in zip(ranks, usernames):
            username_queue.put_nowait((rank, username))


async def player_worker(name, session, username_queue, stats_queue):
    while True:
        await asyncio.sleep(0.2 * random.random())          # Prevent workers getting into lockstep

        rank, username = await username_queue.get()
        if rank == float('inf'):
            await username_queue.put((float('inf'), None))  # Put sentinel back for peers to see
            return

        try:
            player_csv = await pull_player_stats(session, username)
            stats_queue.put_nowait((rank, player_csv))

        except KeyError as e:
            print("user '{}' (rank {}) skipped: {}".format(username, rank, e))
            continue

        except Exception:
            await username_queue.put((rank, username))
            raise


async def run_vpn(respin_vpn, vpn_up):

    # Get VPN locations by parsing the output of `expresso locations`.
    print("getting location codes...", end=' ', flush=True)
    cmd = 'expresso locations'
    output = await run_subprocess(cmd)

    # Parse lines like: "- USA - Chicago (9)" -> 9
    #                   "- India (via UK) (152)" -> 152
    location_codes = []
    for line in output.split('\n'):
        if line.startswith('- USA - Chicago'):
            tmp = line.split(')')[-2]
            code = tmp.split('(')[-1]
            code = int(code)
            location_codes.append((code, line))

    for (code, line) in repeat_shuffled(location_codes):
        location = line[len('- '):].split('(')[0].strip()
        print("respinning vpn ({})...".format(location))
        vpn_up.clear()
        cmd = 'expresso connect --change --random {}'.format(code)
        output = await run_subprocess(cmd)
        await asyncio.sleep(1.0)

        respin_vpn.clear()
        vpn_up.set()
        print("done")

        await respin_vpn.wait()


async def run_scraping(job_queue, stats_queue, respin_vpn, vpn_up):
    page_queue = asyncio.PriorityQueue()
    username_queue = asyncio.PriorityQueue()

    # Run intermediate task which unrolls page information into usernames.
    unzip_task = asyncio.create_task(
        unzip_pages(page_queue, username_queue, bufsize=100)
    )

    while True:
        respin_vpn.set()
        await vpn_up.wait()

        async with aiohttp.ClientSession() as session:
            tasks = []

            # Run hiscores page scrapers.
            for i in range(2):
                tasks.append(asyncio.create_task(
                    page_worker(f'page-worker-{i}', session, job_queue, page_queue)
                ))
                await asyncio.sleep(0.2)

            # Run player stats scrapers.
            for i in range(30):
                tasks.append(asyncio.create_task(
                    player_worker(f'player-worker-{i}', session, username_queue, stats_queue)
                ))
                await asyncio.sleep(0.2)

            done, pending = await asyncio.wait(tasks, timeout=3600, return_when=asyncio.FIRST_EXCEPTION)
            if done:
                for task in done:
                    try:
                        task.result()       # Get exception from task which hit error first.
                    except ApiError as e:
                        print(e)
                        break
                else:
                    break                   # If all tasks completed without error, we're done.

            for task in pending:
                task.cancel()
            for task in pending:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    await unzip_task


async def write_csv(stats_queue, out_file, total_pages):
    with open(out_file, 'a') as f:
        with tqdm(total=total_pages * 25) as pbar:
            while True:
                rank, player_csv = await stats_queue.get()
                f.write(player_csv + '\n')
                pbar.update(1)


async def main(out_file, start_page=1, end_page=80000):
    print("scraping OSRS hiscores data...")
    pages_to_scrape = list(range(start_page, end_page + 1))

    # If output file exists, find out what's already been computed.
    if os.path.isfile(out_file):
        found_pages = defaultdict(set)
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)

            # Deduce hiscores page number from each row of player data.
            print("reading previous results...")
            for line in tqdm(reader):
                rank = int(line[1])
                page_num = (rank - 1) // 25 + 1
                found_pages[page_num].add(rank)

        complete_pages = set()
        for page_num, ranks_on_page in found_pages.items():
            if len(ranks_on_page) == 25:
                complete_pages.add(page_num)

        print("found {} previously completed pages".format(len(complete_pages)))

        pages_to_scrape = list(set(pages_to_scrape) - complete_pages)
        pages_to_scrape = sorted(pages_to_scrape)

    if not pages_to_scrape:
        print("nothing to do")
        return
    else:
        print("{} pages to scrape".format(len(pages_to_scrape)))

    # If output file doesn't exist, create it and write header.
    if not os.path.isfile(out_file):
        skills_file = pathlib.Path(__file__).resolve().parent.parent.parent / 'reference/skills.csv'
        with open(skills_file, 'r') as f:
            skills = f.read().strip().split('\n')
        with open(out_file, 'w') as f:
            f.write(','.join(skills) + '\n')

    job_queue = asyncio.PriorityQueue()
    stats_queue = asyncio.PriorityQueue()
    respin_vpn = asyncio.Event()
    vpn_up = asyncio.Event()

    # Populate job queue with pages to scrape and a sentinel value.
    for page_num in pages_to_scrape:
        job_queue.put_nowait(page_num)
    job_queue.put_nowait(float('inf'))

    tasks = []
    tasks.append(asyncio.create_task(
        run_vpn(respin_vpn, vpn_up)
    ))
    tasks.append(asyncio.create_task(
        run_scraping(job_queue, stats_queue, respin_vpn, vpn_up)
    ))
    tasks.append(asyncio.create_task(
        write_csv(stats_queue, out_file, total_pages=len(pages_to_scrape))
    ))

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    out_file = sys.argv[1]
    start_page = int(sys.argv[2])
    end_page = int(sys.argv[3])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(out_file, start_page, end_page)
    )
