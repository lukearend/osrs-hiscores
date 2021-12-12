#!/usr/bin/env python3

""" Download stats for the top 2 million players on the main OSRS hiscores.
    This scrape can be run repeatedly without destroying previous results.
    Player data is scraped page by page, for each of 80,000 pages containing
    25 players each. Once all pages have been scraped, running this script
    will have no effect.
"""

import asyncio
import csv
import os
import pathlib
import pickle
import random
import sys

import aiohttp
from tqdm import tqdm

from src.scrape import pull_hiscores_page, parse_hiscores_page, repeat_shuffled, run_subprocess


async def run_vpn(vpn_up, vpn_reset):

    # Get VPN locations by parsing the output of `expresso locations`.
    print("getting location codes...", end=' ', flush=True)
    cmd = 'expresso locations'
    output = await run_subprocess(cmd)

    # Parse lines like: "- USA - Chicago (9)" -> 9
    #                   "- India (via UK) (152)" -> 152
    location_codes = []
    for line in output.split('\n'):
        if line.startswith('- '):
            tmp = line.split(')')[-2]
            code = tmp.split('(')[-1]
            code = int(code)
            location_codes.append(code)

    print("done")

    # Switch the VPN whenever we start getting blocked from too many requests.
    for location in repeat_shuffled(location_codes):

        print("resetting vpn connection...", end=' ', flush=True)
        cmd = 'expresso connect --change --random {}'.format(location)
        output = await run_subprocess(cmd)

        print("done (location code {})".format(location))
        vpn_up.set()
        vpn_reset.clear()
        await vpn_reset.wait()


async def page_worker(session, job_queue, out_queue, stop_signal):

    # Spread out workers a bit
    await asyncio.sleep(1 * random.random())

    while not stop_signal.is_set():
        try:
            page_i = job_queue.get_nowait()
            print("got job {}".format(page_i))
        except asyncio.QueueEmpty:
            stop_signal.set()
            break

        try:
            raw_html = await pull_hiscores_page(session, page_i)
            player_info = parse_hiscores_page(raw_html)
            out_queue.put_nowait((page_i, player_info))
            print(page_i, player_info)

        except Exception as e:
            print("failed job {}: {}".format(page_i, e))
            job_queue.put_nowait(page_i)


async def scrape_pages(out_queue, vpn_up, vpn_reset):

    # Download pages in approximate order from 1-80000 with parallel workers.
    # Put raw pages of 25 usernames each on a priority queue which maintains
    # ordering of hiscores ranking.

    num_workers = 1

    job_queue = asyncio.PriorityQueue()
    for page_i in range(1, 80001):
        job_queue.put_nowait(page_i)

    while not job_queue.empty():

        await vpn_up.wait()
        stop_signal = asyncio.Event()

        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[page_worker(session, job_queue, out_queue, stop_signal)
                                   for _ in range(num_workers)])

        vpn_up.clear()
        vpn_reset.set()


async def lookup_players(page_queue, out_queue, vpn_up):
    pass


async def main(out_file):
    print("scraping OSRS hiscores data...")

    page_queue = asyncio.PriorityQueue()
    stats_queue = asyncio.PriorityQueue()

    vpn_up = asyncio.Event()
    vpn_reset = asyncio.Event()

    await asyncio.gather(
        run_vpn(vpn_up, vpn_reset),
        scrape_pages(page_queue, vpn_up, vpn_reset),
        lookup_players(page_queue, stats_queue, vpn_up)
    )

    print("done")

    # Workers read off the raw pages queue and parse HTML, then grab
    # CSV data for each of the 25 players using the CSV API. They write
    # player results to a priority queue to maintain rank ordering.

    # Writer takes latest entries off the player queue in rank order and
    # appends their page number and stats to the CSV data file.

    # When restarted, infer current progress from last row of CSV data file (which is append-only). 

    # file stuff
    file_lock = asyncio.Lock()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(*sys.argv[1:])
    )
    sys.exit(0)


# def process_users(job_queue, out_file, file_lock):
#     with open(out_file, 'a', buffering=1) as f:
#         while True:
#             username = job_queue.get()
#             if username == 'stop':
#                 break

#             try:
#                 stats_csv = request_stats(username)
#             except KeyError as e:
#                 print("could not process user '{}': {}".format(username, e))

#                 file_lock.acquire()
#                 f.write(username + '\n')
#                 file_lock.release()
#                 continue

#             except ValueError as e:
#                 print("could not process user '{}': {}".format(username, e))
#                 continue

#             file_lock.acquire()
#             f.write(stats_csv + '\n')
#             file_lock.release()

#             print('processed user {}'.format(username))


# def process_pages(job_queue, out_file, file_lock):
#     with open(out_file, 'a', buffering=1) as f:
#         while True:
#             page_number = job_queue.get()
#             if page_number == 'stop':
#                 break

#             try:
#                 page = request_page(page_number)
#                 result = parse_page(page)
#             except ValueError as e:
#                 print('could not process page {}: {}'.format(page_number, e))
#                 return

#             file_lock.acquire()
#             for rank, player in result.items():
#                 f.write("{},{},{},{}\n".format(
#                         rank, page_number, player['username'], player['total_level']))
#             file_lock.release()

#             print('processed page {}'.format(page_number))


# def run_workers_once(pages_to_process, out_file):
#     file_lock = Lock()
#     job_queue = Queue()
#     for page in pages_to_process:
#         job_queue.put(page)

#     workers = []
#     for i in range(32):
#         worker = Thread(target=process_pages,
#                         args=(job_queue, out_file, file_lock),
#                         daemon=True)
#         workers.append(worker)
#         job_queue.put('stop')

#     for worker in workers:
#         worker.start()
#     for worker in workers:
#         worker.join()


# def main(out_file):

#     print("scraping usernames...")

#     while True:
#         # There are 80,000 pages, giving rankings 1-25, 26-50, ..., etc.
#         # up to 2 million.
#         pages_to_process = set(range(1, 80001))

#         # Write user rankings as they are processed in a CSV file.
#         # If file is already there, skip the pages it already contains.
#         if os.path.isfile(out_file):

#             print("checking previous results...")
#             with open(out_file, 'r') as f:
#                 reader = csv.reader(f)
#                 processed_pages = [int(line[1]) for line in tqdm(reader)]

#             processed_pages = set(processed_pages)
#             pages_to_process -= processed_pages

#         print("{}/80000 pages left to process".format(len(pages_to_process)))

#         if not pages_to_process:
#             break

#         # Launch the threads once, running all until they have exited
#         # with an error. The threads error out after about 45 seconds
#         # when the Jagex server blocklists this IP for too many requests.
#         # Reset the IP address using the CLI interface to ExpressVPN.
#         print("resetting vpn connection...")
#         location = random.choice(locations)
#         subprocess.run(['expresso', 'connect', '--change', '--random', location])
#         run_workers_once(pages_to_process, out_file)

#     print("done")
#     print()
