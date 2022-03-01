#!/usr/bin/env python3

""" Download stats for the top 2 million players on the OSRS hiscores.
    Like the previous scraping script, this script operates in an
    append-only manner and running it will do nothing once the output
    file contains a complete results set. Running the full scrape
    takes about 18 hours.
"""

import asyncio
import csv
import os
import sys

import aiohttp
from tqdm import tqdm

from src.scrape import request_stats, HiscoresApiError


async def process_stats(session, job_queue, out_file, file_lock, pbar):
    with open(out_file, 'a', buffering=1) as f:
        while True:
            try:
                username = job_queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            try:
                stats_csv = await request_stats(session, username)
            except KeyError as e:
                # Make a row representing the missing data.
                print(f"user '{e}' not found")
                await file_lock.acquire()
                f.write(username + '\n')
                file_lock.release()
                continue
            except HiscoresApiError as e:
                print(f"could not process user '{username}': {e}")
                continue

            await file_lock.acquire()
            f.write(stats_csv + '\n')
            pbar.update(1)
            file_lock.release()


async def run_workers(names_to_scrape, out_file, pbar):
    file_lock = asyncio.Lock()
    job_queue = asyncio.Queue()
    for username in names_to_scrape:
        job_queue.put_nowait(username)

    async with aiohttp.ClientSession() as session:
        workers = []
        for i in range(36):
            workers.append(asyncio.create_task(
                process_stats(session, job_queue, out_file, file_lock, pbar)
            ))
            await asyncio.sleep(0.1)

        await asyncio.gather(*workers)


def main(in_file, out_file):
    """
    :param in_file: read usernames to scrape from this CSV file
    :param out_file: output scraped player data to this CSV file
    """
    print("scraping player stats...")

    # Read user rankings file to see which usernames need to be processed.
    print("reading usernames to scrape...")
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        names_to_scrape = [line[1] for line in tqdm(reader)]
    nplayers = len(names_to_scrape)

    # Check which usernames have been processed already.
    if os.path.isfile(out_file):
        print("output file detected, scanning existing results...")
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            processed_names = [line[0] for line in tqdm(reader)]

        names_to_scrape = set(names_to_scrape) - set(processed_names)

    if not names_to_scrape:
        return True

    print(f"{len(names_to_scrape)}/{nplayers} users left to process")

    with tqdm(total=nplayers, initial=nplayers - len(names_to_scrape)) as pbar:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_workers(names_to_scrape, out_file, pbar)
        )
        return False


if __name__ == '__main__':
    done = main(*sys.argv[1:])

    if done:
        print("done")
        sys.exit(0)
    sys.exit(1)
