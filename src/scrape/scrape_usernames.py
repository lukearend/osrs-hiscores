#!/usr/bin/env python3

""" Download usernames for the top 2 million players on the OSRS hiscores.
    This script is meant to be run repeatedly and will only append new
    results to the output file, skipping any pages previously scraped.
    Once the output file contains a complete set of results, running
    this script against it will do nothing and return with exit code 0.
    Running the full scrape takes about 90 mins.
"""
import argparse
import asyncio
import csv
import os
import sys
from collections import defaultdict

from tqdm import tqdm

from src.scrape import request_hiscores_page, parse_page_html, run_workers


async def process_pages(session, job_queue, out_file, file_lock, pbar):
    with open(out_file, 'a', buffering=1) as f:
        while True:
            try:
                page_number = job_queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            page = await request_hiscores_page(session, page_number)
            result = parse_page_html(page)

            await file_lock.acquire()
            for rank, player in result.items():
                f.write(f"{rank},{page_number},{player['username']},{player['total_level']}\n")
            pbar.update(1)
            file_lock.release()


def main(out_file: str, start_page: int, end_page: int):
    print("scraping usernames...")

    if start_page > end_page:
        raise ValueError(f"start page {start_page}) is greater than end page {end_page}")

    # There are 80,000 pages, giving rankings 1-25, 26-50, ..., etc. up to 2 million.
    total_pages = end_page - start_page + 1
    pages_to_scrape = set(range(start_page, end_page + 1))

    # Write ranked usernames as they are extracted from pages into a CSV file.
    # If that file exists, find out what's already been computed.
    if os.path.isfile(out_file):
        found_pages = defaultdict(set)
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # discard header

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

    print(f"{len(pages_to_scrape)}/80000 pages left to scrape")

    with tqdm(total=total_pages, initial=total_pages - len(pages_to_scrape)) as pbar:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            run_workers(process_pages, pages_to_scrape, out_file, pbar, nworkers=24)
        )
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape the top 2 million usernames from the OSRS hiscores.""")
    parser.add_argument('outfile', type=str, help="dump scraped usernames to this CSV file")
    parser.add_argument('-s', '--start', type=int, help="start at this page number (default is 1)")
    parser.add_argument('-e', '--end', type=int, help="stop after this page (default is 80000, max 80000)")
    args = parser.parse_args()
    done = main(args.outfile, args.start, args.end)
    if done:
        print("done")
        sys.exit(0)
    sys.exit(1)
