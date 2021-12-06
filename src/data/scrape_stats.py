#!/usr/bin/env python3

""" Download stats for the top 2 million players on the OSRS hiscores.
    Like the previous scraping script, this script operates in an
    append-only manner and running it will do nothing once the output
    file contains a complete results set.
"""

import csv
import os
import pickle
import random
import subprocess
import sys
from queue import Queue
from threading import Thread, Lock

from tqdm import tqdm

from src.data import request_stats, parse_stats


def process_pages(job_queue, out_file, file_lock):
    with open(out_file, 'a', buffering=1) as f:
        while True:
            username = job_queue.get()
            if username == 'stop':
                break

            try:
                stats_csv = request_stats(username)
            except KeyError as e:
                print("could not process user '{}': {}".format(username, e))

                file_lock.acquire()
                f.write(username + '\n')
                file_lock.release()
                continue

            except ValueError as e:
                print("could not process user '{}': {}".format(username, e))
                continue

            file_lock.acquire()
            f.write(stats_csv + '\n')
            file_lock.release()

            print('processed user {}'.format(username))


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
    print("scraping stats...")

    # Read user rankings file to see which usernames need to be processed.
    print("reading file of usernames to scrape...")
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        names_to_process = [line[1] for line in tqdm(reader)]
    num_players = len(names_to_process)

    # Check which usernames have been processed already.
    if os.path.isfile(out_file):

        print("output file detected, reading existing results...")
        with open(out_file, 'r') as f:
            reader = csv.reader(f)
            processed_names = [line[0] for line in tqdm(reader)]

        names_to_process = set(names_to_process) - set(processed_names)

    print("{}/{} users left to process".format(len(names_to_process), num_players))

    if not names_to_process:
        print("done scraping stats")
        return

    run_workers_once(names_to_process, out_file)
    print("done scraping stats")


if __name__ == '__main__':
    main(*sys.argv[1:])
