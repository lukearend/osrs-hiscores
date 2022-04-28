#!/usr/bin/env python3

""" Scrape stats from the OSRS hiscores into a CSV file. """

import argparse
import asyncio
import logging
import sys
import traceback

from src.scrape.exceptions import RequestFailed
from src.scrape.export import get_top_rank
from src.scrape.scrape import scrape_hiscores, N_PAGE_WORKERS
from src.scrape.vpn import reset_vpn, askpass


def logprint(msg, level):
    logger = getattr(logging, level.lower())
    logger(msg)
    print(msg)


def main(out_file: str, start_rank: int, stop_rank: int, num_workers: int = 28,
         use_vpn: bool = False, sudo_password: str = None) -> int:
    """ Scrape players from the OSRS hiscores into a CSV file. """

    logprint(f"starting to scrape (ranks {start_rank}-{stop_rank}, "
             f"{num_workers} stats workers)", level='info')

    while True:
        last_rank = get_top_rank(out_file)
        if last_rank and last_rank >= start_rank:
            start_rank = last_rank + 1
            logprint(f"found an existing record at rank {last_rank},"
                     f"continuing from {start_rank}", level='info')

        if use_vpn:
            reset_vpn(sudo_password)

        try:
            asyncio.run(scrape_hiscores(start_rank, stop_rank, out_file, num_workers))
        except RequestFailed as e:
            if use_vpn:
                logging.error(f"caught RequestFailed: {e}")
                continue
            raise

    logprint("done", 'info')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Download player data from the OSRS hiscores.")
    parser.add_argument('--start-rank', required=True, type=int, help="start data collection at this player rank")
    parser.add_argument('--stop-rank', required=True, type=int, help="stop data collection at this rank")
    parser.add_argument('--out-file', required=True, help="dump scraped data to this CSV file in append mode")
    parser.add_argument('--num-workers', default=28, type=int, help="number of concurrent scraping threads")
    parser.add_argument('--log-file', default=None, help="if provided, output logs to this file")
    parser.add_argument('--log-level', default='info', help="'debug'|'info'|'warning'|'error'|'critical'")
    parser.add_argument('--vpn', action='store_true', help="if set, will use VPN")
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
        sys.exit(2)

    sudo_pwd = None
    if args.vpn:
        sudo_pwd = askpass()

    try:
        main(args.out_file, args.start_rank, args.stop_rank, args.num_workers, args.vpn, sudo_pwd)
    except Exception as e:
        logprint(traceback.format_exc(), 'critical')
        logprint("exiting", 'info')
        sys.exit(1)
