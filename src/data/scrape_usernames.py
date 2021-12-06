#!/usr/bin/env python3

""" Download usernames for the top 2 million players on the OSRS hiscores.
    This script is made so it can be run repeatedly and will only append
    new results to the output file, skipping any pages previously scraped.
    Once the output file is complete, running this script will do nothing.
"""

import csv
import os
import pathlib
import pickle
import random
import subprocess
import sys
from queue import Queue
from threading import Thread, Lock

from tqdm import tqdm

from src.data import request_page, parse_page


def process_pages(job_queue, out_file, file_lock):
    with open(out_file, 'a', buffering=1) as f:
        while True:
            page_number = job_queue.get()
            if page_number == 'stop':
                break

            try:
                page = request_page(page_number)
                result = parse_page(page)
            except ValueError as e:
                print('could not process page {}: {}'.format(page_number, e))
                return

            file_lock.acquire()
            for rank, player in result.items():
                f.write("{},{},{},{}\n".format(
                        rank, page_number, player['username'], player['total_level']))
            file_lock.release()

            print('processed page {}'.format(page_number))


def run_workers_once(pages_to_process, out_file):
    file_lock = Lock()
    job_queue = Queue()
    for page in pages_to_process:
        job_queue.put(page)

    workers = []
    for i in range(32):
        worker = Thread(target=process_pages,
                        args=(job_queue, out_file, file_lock),
                        daemon=True)
        workers.append(worker)
        job_queue.put('stop')

    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


def main(out_file):
    # VPN location codes are written as a pickled list of integers.
    # These were obtained by parsing the output of `expresso locations`.
    locations_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/vpnlocations.pkl'
    with open(locations_file, 'rb') as f:
        locations = pickle.load(f)

    print("scraping usernames...")

    while True:
        # There are 80,000 pages, giving rankings 1-25, 26-50, ..., etc.
        # up to 2 million.
        pages_to_process = set(range(1, 80001))

        # Write user rankings as they are processed in a CSV file.
        # If file is already there, skip the pages it already contains.
        if os.path.isfile(out_file):

            print("output file detected, reading existing results...")
            with open(out_file, 'r') as f:
                reader = csv.reader(f)
                processed_pages = [int(line[1]) for line in tqdm(reader)]

            processed_pages = set(processed_pages)
            pages_to_process -= processed_pages

        print("{}/80000 pages left to process".format(len(pages_to_process)))

        if not pages_to_process:
            break

        # Launch the threads once, running all until they have exited
        # with an error. The threads error out after about 45 seconds
        # when the Jagex server blocklists this IP for too many requests.
        # Reset the IP address using the CLI interface to ExpressVPN.
        print("resetting vpn connection...")
        location = random.choice(locations)
        subprocess.run(['expresso', 'connect', '--change', '--random', location])
        run_workers_once(pages_to_process, out_file)

    print("done scraping usernames")


if __name__ == '__main__':
    main(*sys.argv[1:])
