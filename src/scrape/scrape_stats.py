#!/usr/bin/env python3

""" Download stats for the top 2 million players on the OSRS hiscores.
    Like the previous scraping script, this script operates in an
    append-only manner and running it will do nothing once the output
    file contains a complete results set.
"""

import csv
import os
import sys
from queue import Queue
from threading import Thread, Lock

from tqdm import tqdm


def run_workers_once(names_to_process, out_file):
    file_lock = Lock()
    job_queue = Queue()
    for username in names_to_process:
        job_queue.put(username)

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


def main(in_file, out_file):
    print("scraping player stats...")

    # Read user rankings file to see which usernames need to be processed.
    print("reading usernames to scrape...")
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        names_to_process = [line[1] for line in tqdm(reader)]
    num_players = len(names_to_process)

    # Check which usernames have been processed already.
    if os.path.isfile(out_file):

        print("output file detected, scanning existing results...")
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            processed_names = [line[0] for line in tqdm(reader)]

        names_to_process = set(names_to_process) - set(processed_names)

    print("{}/{} users left to process".format(len(names_to_process), num_players))

    if not names_to_process:
        print()
        return

    run_workers_once(names_to_process, out_file)

    print("done")
    print()


if __name__ == '__main__':
    main(*sys.argv[1:])
