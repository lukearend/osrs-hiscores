""" Shared classes for the scraping process. """

from datetime import datetime
from typing import List

import numpy as np


class DoneScraping(Exception):
    """ Raised when all scraping is done. """


class NothingToDo(Exception):
    """ Raised upon discovering the output file is already complete. """


class UserNotFound(Exception):
    """ Raised when data for a requested username does not exist. """


class ServerBusy(Exception):
    """ Raised when the CSV API is too busy to process a stats request. """


class RequestFailed(Exception):
    """ Raised when an HTTP request to the hiscores API fails. """

    def __init__(self, message, code=None):
        self.code = code
        super().__init__(message)


class PlayerRecord:
    """ Data record for one player scraped from the hiscores. """

    def __init__(self, username: str, stats: List[int], ts: datetime):
        self.username = username

        # First three stats are rank,
        self.total_level = stats[1]
        self.total_xp = stats[2]
        self.rank = stats[0]
        self.stats = np.array(stats).astype('int')
        self.ts = ts

    def __lt__(self, other):
        if self.total_level < other.total_level:
            return True
        elif self.total_level == other.total_level and self.total_xp < other.total_xp:
            return True
        elif self.total_xp == other.total_xp and self.rank > other.rank:  # worse players have higher ranks
            return True
        return False

    def __eq__(self, other):
        if other is None:
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
