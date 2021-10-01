import csv
import os
import pickle
import random
import subprocess
from queue import Queue
from threading import Thread, Lock

from hiscores.data import request_stats, parse_stats


NUM_WORKERS = 32
IN_FILE = '../../data/interim/usernames.csv'
OUT_FILE = '../../data/raw/stats-raw.csv'


def process_pages(job_queue, file_lock):
    with open(OUT_FILE, 'a', buffering=1) as f:
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


def run_workers_once(names_to_process):
    file_lock = Lock()
    job_queue = Queue()
    for username in names_to_process:
        job_queue.put(username)

    workers = []
    for i in range(NUM_WORKERS):
        worker = Thread(target=process_pages,
                        args=(job_queue, file_lock),
                        daemon=True)
        workers.append(worker)
        job_queue.put('stop')

    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


def main():
    # Read user rankings file to see which usernames need to be processed.
    with open(IN_FILE, 'r') as f:
        reader = csv.reader(f)
        names_to_process = [line[1] for line in reader]

    # Check which usernames have been processed already.
    print("checking stats progress so far...")
    if os.path.isfile(OUT_FILE):
        with open(OUT_FILE, 'r') as f:
            reader = csv.reader(f)
            processed_names = [line[0] for line in reader]

        names_to_process = set(names_to_process) - set(processed_names)

    print("found {} users to process".format(len(names_to_process)))

    if not names_to_process:
        print("done scraping stats")
        return

    run_workers_once(names_to_process)
    print("done scraping stats")


if __name__ == '__main__':
    main()
