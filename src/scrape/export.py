import csv
import os
from asyncio import Queue
from datetime import datetime

from tqdm import tqdm

from src import csv_api_stats
from src.scrape import PlayerRecord, CSV_HEADER, STATS_RANK_COL, STATS_TOTLVL_COL, STATS_TOTXP_COL

from src.scrape.workers import JobCounter


class DoneScraping(Exception):
    """ Raised when all scraping is done to indicate script should exit. """


async def progress_bar(ndone: JobCounter, ntodo: int):
    with tqdm(total=ntodo, smoothing=0.9) as pbar:
        while True:
            await ndone.await_next()
            pbar.n = ndone.value
            pbar.refresh()
            if ndone.value == ntodo:
                raise DoneScraping


async def export_records(in_queue: Queue, out_file: str, job_counter: JobCounter):
    """ Write player records appearing on a queue to a CSV file. """

    mode = 'w' if not os.path.isfile(out_file) else 'a'
    with open(out_file, 'a') as f:
        if mode == 'w':
            csv.writer(f).writerow(CSV_HEADER)
        while True:
            player: PlayerRecord = await in_queue.get()
            if player != 'notfound':
                f.write(player_to_csv(player) + '\n')
            job_counter.next()


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


def csv_to_player(csv_line: str) -> PlayerRecord:
    username, *stats, ts = csv_line.split(',')
    stats = [int(v) if v else None for v in stats]
    assert len(stats) == len(csv_api_stats()), f"CSV row contained an unexpected number of stats: '{csv_line}'"
    return PlayerRecord(
        username=username,
        rank=stats[STATS_RANK_COL],
        total_level=stats[STATS_TOTLVL_COL],
        total_xp=stats[STATS_TOTXP_COL],
        stats=stats,
        ts=datetime.fromisoformat(ts)
    )


def player_to_csv(player: PlayerRecord) -> str:
    stats = [str(v) if v else '' for v in player.stats]
    fields = [player.username] + stats + [player.ts.isoformat()]
    return ','.join(fields)
