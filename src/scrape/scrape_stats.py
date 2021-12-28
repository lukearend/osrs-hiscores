#!/usr/bin/env python3

""" Download stats for the top 2 million players on the OSRS hiscores.
    Like the previous scraping script, this script operates in an
    append-only manner and running it will do nothing once the output
    file contains a complete results set.
"""

import asyncio
import csv
import os
import sys

import aiohttp
from tqdm import tqdm

from src.scrape import request_stats


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
                print("could not find user '{}': {}".format(username, e))

                # Make a row representing the missing data.
                await file_lock.acquire()
                f.write(username + '\n')
                file_lock.release()
                continue

            except ValueError as e:
                print("could not process user '{}': {}".format(username, e))
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
    job_queue.put_nowait(None)

    async with aiohttp.ClientSession() as session:
        workers = []
        for i in range(36):
            workers.append(asyncio.create_task(
                process_stats(session, job_queue, out_file, file_lock, pbar)
            ))
            await asyncio.sleep(0.1)

        await asyncio.gather(*workers)


def main(in_file, out_file):
    print("scraping player stats...")

    # Read user rankings file to see which usernames need to be processed.
    print("reading usernames to scrape...")
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        names_to_scrape = [line[1] for line in tqdm(reader)]
    num_players = len(names_to_scrape)

    # Check which usernames have been processed already.
    if os.path.isfile(out_file):
        print("output file detected, scanning existing results...")
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            processed_names = [line[0] for line in tqdm(reader)]

        names_to_scrape = set(names_to_scrape) - set(processed_names)

    print("{}/{} users left to process".format(len(names_to_scrape), num_players))

    if not names_to_scrape:
        return True

    with tqdm(total=num_players, initial=num_players - len(names_to_scrape)) as pbar:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_workers(names_to_scrape, out_file, pbar)
        )
        return False


if __name__ == '__main__':
    done = main(*sys.argv[1:])
    if done:
        print("done")
        print()
        sys.exit(0)
    sys.exit(1)
