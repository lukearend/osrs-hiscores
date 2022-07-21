#!/usr/bin/env python3

""" Scrape data from the OSRS hiscores into a CSV file. """

import argparse
import asyncio
import logging
import sys
import traceback

import aiohttp

from src.scrape.common import RequestFailed
from src.scrape.export import get_top_rank, get_page_jobs, export_records
from src.scrape.common import DoneScraping
from src.scrape.workers import JobQueue, JobCounter, Worker, \
    request_page, request_stats, enqueue_page_usernames, enqueue_stats


N_PAGE_WORKERS = 2   # number of page workers downloading rank/username info
UNAME_BUFSIZE = 100  # maximum length of buffer containing username jobs for stats workers


def logprint(msg, level):
    logger = getattr(logging, level.lower())
    logger(msg)
    print(msg)


async def main(out_file: str, start_rank: int, stop_rank: int, num_workers: int):
    """ Scrape hiscores data until hitting an exception. """

    # Build the job queues connecting each stage of the processing pipeline.
    joblist = get_page_jobs(start_rank, stop_rank)
    page_q = JobQueue()
    for job in joblist:
        await page_q.put(job)
    uname_q = JobQueue(maxsize=UNAME_BUFSIZE)
    export_q = asyncio.Queue()

    # Scraping happens in two stages. First the page workers download front pages
    # of the hiscores and extract usernames in ranked order. Then the stats workers
    # receive usernames and query the CSV API for the corresponding account stats.
    currentpage = JobCounter(value=joblist[0].pagenum)
    pageworkers = [Worker(in_queue=page_q, out_queue=uname_q, job_counter=currentpage)
                   for _ in range(N_PAGE_WORKERS)]

    currentrank = JobCounter(value=start_rank)
    statworkers = [Worker(in_queue=uname_q, out_queue=export_q, job_counter=currentrank)
                   for _ in range(num_workers)]

    # Spawn the data scraping tasks and run until requests fail.
    async with aiohttp.ClientSession() as sess:
        T = [asyncio.create_task(
            export_records(in_queue=export_q, out_file=out_file, total=stop_rank - currentrank.value + 1)
        )]
        for w in pageworkers:
            T.append(asyncio.create_task(
                w.run(sess, request_fn=request_page, enqueue_fn=enqueue_page_usernames)
            ))
        for i, w in enumerate(statworkers):
            T.append(asyncio.create_task(
                w.run(sess, request_fn=request_stats, enqueue_fn=enqueue_stats, delay=i * 0.1)
            ))
        try:
            await asyncio.gather(*T)  # allow first exception to be caught
        except DoneScraping:
            pass
        finally:
            for task in T:
                task.cancel()
            await asyncio.gather(*T, return_exceptions=True)  # suppress CancelledErrors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Download player data from the OSRS hiscores.")
    parser.add_argument('--start-rank', required=True, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', required=True, type=int, help="stop data collection at this rank")
    parser.add_argument('--out-file', required=True, help="dump scraped data to this CSV file in append mode")
    parser.add_argument('--num-workers', default=28, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--log-file', default=None, help="if provided, output logs to this file")
    parser.add_argument('--log-level', default='info', help="'debug'|'info'|'warning'|'error'|'critical'")
    args = parser.parse_args()

    if args.log_file:
        logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                            datefmt="%H:%M:%S", level=getattr(logging, args.log_level.upper()),
                            handlers=[logging.FileHandler(filename=args.log_file, mode='a')])
    else:
        logging.disable()

    # The remote server seems to have a connection limit of 30.
    if args.num_workers + N_PAGE_WORKERS > 30:
        raise ValueError(f"too many stats workers, maximum allowed is {30 - N_PAGE_WORKERS}")

    existing_rank = get_top_rank(args.out_file)
    if existing_rank and existing_rank >= args.stop_rank:
        logprint("nothing to do", level='info')
        sys.exit(0)

    logprint(f"starting to scrape (ranks {args.start_rank}-{args.stop_rank}, "
             f"{args.num_workers} stats workers)", level='info')

    last_rank = get_top_rank(args.out_file)
    if last_rank and last_rank >= args.start_rank:
        args.start_rank = last_rank + 1
        logprint(f"found an existing record at rank {last_rank},"
                 f"continuing from {args.start_rank}", level='info')

    try:
        asyncio.run(main(args.out_file, args.start_rank, args.stop_rank, args.num_workers))
    except RequestFailed as e:
        logging.error(f"caught RequestFailed: {e}")
        sys.exit(1)
    except Exception as e:
        logprint(traceback.format_exc(), 'critical')
        sys.exit(2)

    logprint("done", 'info')
    sys.exit(0)
