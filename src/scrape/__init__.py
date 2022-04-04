""" Classes and functions used throughout the scraping module. """

import asyncio
import logging
from datetime import datetime
from typing import List

from src import csv_api_stats


class RequestFailed(Exception):
    """ Raised when an HTTP request to the hiscores API fails. """

    def __init__(self, message, code=None):
        self.code = code
        super().__init__(message)


class UserNotFound(Exception):
    """ Raised when data for a requested username does not exist. """


class ServerBusy(Exception):
    """ Raised when the CSV API is too busy to process a stats request. """


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


class PlayerRecord:
    """ Data record for one player scraped from the hiscores. """

    RANK_COL = csv_api_stats().index('total_rank')
    TOTLVL_COL = csv_api_stats().index('total_level')
    TOTXP_COL = csv_api_stats().index('total_xp')

    def __init__(self, username: str, stats: List[int], ts: datetime):
        """
        :param username: username of player
        :param stats: list of stat fields in order of raw CSV from hiscores
        :param ts: time at which record was scraped
        """
        self.username = username
        self.stats = stats
        self.total_level = stats[self.TOTLVL_COL]
        self.total_xp = stats[self.TOTXP_COL]
        self.rank = stats[self.RANK_COL]
        self.ts = ts

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


def player_to_csv(player: PlayerRecord) -> str:
    stats = [str(v) if v else '' for v in player.stats]
    fields = [player.username] + stats + [player.ts.isoformat()]
    return ','.join(fields)


def csv_to_player(csv_line: str) -> PlayerRecord:
    username, *stats, ts = csv_line.split(',')
    stats = [int(v) if v else None for v in stats]
    assert len(stats) == len(csv_api_stats()), f"CSV row contained an unexpected number of stats: '{csv_line}'"
    return PlayerRecord(username=username, stats=stats, ts=datetime.fromisoformat(ts))


def logprint(msg, level):
    print(msg)
    logger = getattr(logging, level.lower())
    logger(msg)
