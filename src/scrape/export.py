""" Code for exporting scraped data. """

import asyncio
import csv
import os
from datetime import datetime
from typing import List

from tqdm import tqdm

from src.common import csv_api_stats
from src.scrape.common import DoneScraping, PlayerRecord
from src.scrape.workers import PageJob


async def export_records(in_queue: asyncio.Queue, out_file: str, total: int):
    """ Write player records appearing on a queue to a CSV file. """

    exists = os.path.isfile(out_file)
    with open(out_file, mode='a' if exists else 'w') as f:
        if not exists:
            csv_header = ['username'] + csv_api_stats() + ['ts']
            csv.writer(f).writerow(csv_header)

        for _ in tqdm(range(total), smoothing=0.01):
            player: PlayerRecord = await in_queue.get()
            if player is not None:
                f.write(player_to_csv(player) + '\n')
        raise DoneScraping


def get_top_rank(scrape_file) -> int:
    """ Get the highest rank so far in the CSV file created by scraping. """

    if not os.path.isfile(scrape_file):
        return None

    with open(scrape_file, 'rb') as f:
        f.seek(0, os.SEEK_END)
        try:
            f.seek(-1024, os.SEEK_CUR)
        except OSError:  # file too small to read
            return None
        last_lines = f.read().decode('utf-8').strip().split('\n')
        if len(last_lines) <= 1:
            return None

    return csv_to_player(last_lines[-1]).rank


def get_page_jobs(start_rank: int, end_rank: int) -> List[PageJob]:
    """ Get the list of front pages that need to be scraped for usernames based on
    the desired range of rankings to scrape.

    :param start_rank: lowest player ranking to include in scraping
    :param end_rank: highest player ranking to include in scraping
    :return: list of page jobs to do
    """
    if start_rank < 1:
        raise ValueError("start rank cannot be less than 1")
    if end_rank > 2_000_000:
        raise ValueError("end rank cannot be greater than 2 million")
    if start_rank > end_rank:
        raise ValueError("start rank cannot be greater than end rank")

    firstpage = (start_rank - 1) // 25 + 1  # first page number (value between 1 and 80000)
    lastpage = (end_rank - 1) // 25 + 1     # last page number (value between 1 and 8000)
    startind = (start_rank - 1) % 25        # start for range of page rows to take (value between 0 and 24)
    endind = (end_rank - 1) % 25 + 1        # end for range of page rows to take (value between 1 and 25)

    jobs = []
    for pagenum in range(firstpage, lastpage + 1):
        jobs.append(PageJob(priority=pagenum, pagenum=pagenum,
                            startind=startind if pagenum == firstpage else 0,
                            endind=endind if pagenum == lastpage else 25))
    return jobs


def player_to_csv(player) -> str:
    stats = [str(v) if v else '' for v in player.stats]
    fields = [player.username] + stats + [player.ts.isoformat()]
    return ','.join(fields)


def csv_to_player(csv_line, check_len=False):
    username, *stats, ts = csv_line.split(',')
    if check_len:  # check that length of results is consistent with current API definition
        assert len(stats) == len(csv_api_stats()), f"CSV row contained an unexpected number of stats: '{csv_line}'"
    stats = [int(v) if v else -1 for v in stats]
    return PlayerRecord(username=username, stats=stats, ts=datetime.fromisoformat(ts))
