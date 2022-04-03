import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from src import csv_api_stats

CSV_HEADER = ['username'] + csv_api_stats() + ['ts']
STATS_RANK_COL = csv_api_stats().index('total_rank')
STATS_TOTLVL_COL = csv_api_stats().index('total_level')
STATS_TOTXP_COL = csv_api_stats().index('total_xp')


class RequestFailed(Exception):
    """ Raised when an HTTP request to the hiscores API fails. """

    def __init__(self, message, code=None):
        self.code = code
        super().__init__(message)


class UserNotFound(Exception):
    """ Raised when data for a requested username does not exist. """


class ServerBusy(Exception):
    """ Raised when the CSV API is too busy to process a stats request. """


@dataclass
class PlayerRecord:
    """ Contains data for one player scraped from the hiscores. """

    total_level: int
    total_xp: int
    rank: int
    username: str
    stats: List[int]  # list of stat fields in order of raw CSV from hiscores
    ts: datetime      # time at which record was scraped

    def __lt__(self, other):
        if self.total_level < other.total_level:
            return True
        elif self.total_xp < other.total_xp:
            return True
        elif other.rank < self.rank:  # higher rank means worse player
            return True
        return False

    def __eq__(self, other):
        if other == 'notfound':
            return False
        return not self < other and not other < self

    def __ne__(self, other):
        return not self == other
    def __gt__(self, other):
        return other < self
    def __ge__(self, other):
        return not self < other
    def __le__(self, other):
        return not other < self


class JobCounter:
    """ A counter shared among workers to track the job currently being enqueued. """

    def __init__(self, value: int):
        self.v = value
        self.nextcalled = asyncio.Event()

    @property
    def value(self):
        return self.v

    def next(self, n=1):
        self.v += n
        self.nextcalled.set()

    async def await_next(self):
        await self.nextcalled.wait()
        self.nextcalled.clear()


def get_page_range(start_rank: int, end_rank: int) -> Tuple[int, int, int, int]:
    """ Get the range of front pages that need to be scraped for usernames based on a
    range of rankings to be scraped. The "front pages" are the 80000 pages containing
    ranks for the top 2 million players. Each page provides 25 rank/username pairs,
    such that page 1 contains ranks 1-25, page 2 contains ranks 26-50, etc.

    :param start_rank: lowest player ranking to include in scraping
    :param end_rank: highest player ranking to include in scraping
    :return:
        - first page number (value between 1 and 80000)
        - index of first row in first page to use (value between 0 and 24)
        - last page number (value between 1 and 8000)
        - index of last row in last page to use (value between 0 and 24)
    """
    if start_rank < 1:
        raise ValueError("start rank cannot be less than 1")
    if end_rank > 2_000_000:
        raise ValueError("end rank cannot be greater than 2 million")
    if start_rank > end_rank:
        raise ValueError("start rank cannot be greater than end rank")

    firstpage = (start_rank - 1) // 25 + 1
    lastpage = (end_rank - 1) // 25 + 1
    startind = (start_rank - 1) % 25
    endind = (end_rank - 1) % 25 + 1

    return firstpage, startind, lastpage, endind
