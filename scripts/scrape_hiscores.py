""" Scrapes stats from the OSRS hiscores into a CSV file. Returns
error code 2 if CSV file already contains the requested data range. """

import argparse
import asyncio
import logging
import sys
import traceback

import aiohttp
from codetiming import Timer

from src.scrape import RequestFailed, JobCounter, logprint
from src.scrape.export import DoneScraping, export_records, get_top_rank, get_page_jobs
from src.scrape.workers import JobQueue, Worker, request_stats, enqueue_stats, request_page, enqueue_page_usernames
from src.scrape.vpn import reset_vpn, askpass


N_PAGE_WORKERS = 2   # number of page workers downloading rank/username info
UNAME_BUFSIZE = 100  # maximum length of buffer containing username jobs for stats workers


class NothingToDo(Exception):
    """ Raised if the script discovers the output file is already complete. """


async def main(out_file: str, start_rank: int, stop_rank: int, nworkers: int = 28,
               use_vpn: bool = False, sudo_password: str = None):
    """ Scrape players between the given range of ranks from the
    OSRS hiscores into a CSV file. If `vpn_pass` is provided, the
    VPN is used and sudo-authenticated with the given password. """

    # Check for existing progress.
    highest_rank = get_top_rank(out_file)
    if highest_rank is not None and highest_rank >= start_rank:
        logprint(f"found an existing record at rank {highest_rank}", level='info')
        if highest_rank >= stop_rank:
            raise NothingToDo
        start_rank = highest_rank + 1
        logprint(f"starting from {start_rank}", level='info')

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
                   for _ in range(nworkers)]

    logprint(f"starting to scrape (ranks {start_rank}-{stop_rank}, {nworkers} stats workers)", level='info')
    t = Timer(text="done ({minutes:.1f} minutes)")
    t.start()

    while True:
        if use_vpn:
            reset_vpn(sudo_password)

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
                break
            except RequestFailed as e:
                logging.error(f"caught RequestFailed: {e}")
                if not use_vpn:
                    raise
                continue
            finally:
                for task in T:
                    task.cancel()
                await asyncio.gather(*T, return_exceptions=True)  # suppress CancelledErrors

    t.stop()
    logging.info("done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Download player data from the OSRS hiscores.""")
    parser.add_argument('outfile', help="dump scraped data to this CSV file in append mode")
    parser.add_argument('--start-rank', default=1, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', default=2000000, type=int, help="stop data collection at this rank")
    parser.add_argument('--num-workers', default=28, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--log-file', default=None, help="if provided, output logs to this file")
    parser.add_argument('--log-level', default='info', help="'debug'|'info'|'warning'|'error'|'critical'")
    parser.add_argument('--vpn', dest='vpn', action='store_true', help="if set, will use VPN")
    args = parser.parse_args()

    if args.log_file:
        logging.basicConfig(format="%(asctime)s.%(msecs)03d:%(levelname)s:%(message)s",
                            datefmt="%H:%M:%S", level=getattr(logging, args.log_level.upper()),
                            handlers=[logging.FileHandler(filename=args.log_file, mode='w')])
    else:
        logging.disable()

    # The remote server seems to have a connection limit of 30.
    if args.num_workers + N_PAGE_WORKERS > 30:
        raise ValueError(f"too many stats workers, maximum allowed is {30 - N_PAGE_WORKERS}")

    sudo_pwd = None
    if args.vpn:
        sudo_pwd = askpass()

    try:
        asyncio.run(main(args.outfile, args.start_rank, args.stop_rank, args.num_workers, args.vpn, sudo_pwd))
    except NothingToDo:
        logprint("nothing to do", level='info')
        sys.exit(2)
    except Exception as e:
        print(f"error: {e}")
        logging.critical(traceback.format_exc())
        logging.info("exiting")
        sys.exit(1)
