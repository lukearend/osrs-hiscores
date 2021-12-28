#!/usr/bin/env python3

""" Download usernames for the top 2 million players on the OSRS hiscores.
    This script is made so it can be run repeatedly and will only append
    new results to the output file, skipping any pages previously scraped.
    Once the output file is complete, running this script will do nothing.
"""

import asyncio
import csv
import os
import pickle
import random
import subprocess
import sys
from collections import defaultdict

import aiohttp
from tqdm import tqdm

from src.scrape import request_page, parse_page


async def process_pages(session, job_queue, out_file, file_lock, pbar):
    with open(out_file, 'a', buffering=1) as f:
        while True:
            try:
                page_number = job_queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            page = await request_page(session, page_number)
            result = parse_page(page)

            await file_lock.acquire()
            for rank, player in result.items():
                f.write("{},{},{},{}\n".format(
                        rank, page_number, player['username'], player['total_level']))
            pbar.update(1)
            file_lock.release()


async def run_workers(pages_to_scrape, out_file, pbar):
    file_lock = asyncio.Lock()
    job_queue = asyncio.Queue()
    for page in pages_to_scrape:
        job_queue.put_nowait(page)

    async with aiohttp.ClientSession() as session:
        workers = []
        for i in range(24):
            workers.append(asyncio.create_task(
                process_pages(session, job_queue, out_file, file_lock, pbar)
            ))
            await asyncio.sleep(0.1)

        await asyncio.gather(*workers)


def main(out_file):
    print("scraping usernames...")

    # There are 80,000 pages, giving rankings 1-25, 26-50, ..., etc. up to 2 million.
    pages_to_scrape = set(range(1, 80001))

    # Write ranked usernames as they are extracted from pages into a CSV file.
    # If that file exists, find out what's already been computed.
    if os.path.isfile(out_file):
        found_pages = defaultdict(set)
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)

            print("reading previous results...")
            for line in tqdm(reader):
                rank = int(line[0])
                page_num = int(line[1])
                found_pages[page_num].add(rank)

        complete_pages = set()
        for page_num, ranks_on_page in found_pages.items():
            if len(ranks_on_page) == 25:
                complete_pages.add(page_num)

        pages_to_scrape = list(set(pages_to_scrape) - complete_pages)
        pages_to_scrape = sorted(pages_to_scrape)

    if not pages_to_scrape:
        return True

    print("{}/80000 pages left to scrape".format(len(pages_to_scrape)))

    with tqdm(total=80000, initial=80000 - len(pages_to_scrape)) as pbar:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_workers(pages_to_scrape, out_file, pbar)
        )
        return False


if __name__ == '__main__':
    done = main(*sys.argv[1:])
    if done:
        print("done")
        print()
        sys.exit(0)
    sys.exit(1)
