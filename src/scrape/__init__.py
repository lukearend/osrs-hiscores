import dataclasses
import logging
from typing import Any, Dict, Tuple

from src.scrape.requests import PlayerRecord


def printlog(msg, level):
    print(msg)
    logger = getattr(logging, level.lower())
    logger(msg)


def get_page_range(start_rank: int, end_rank: int) -> Tuple[int, int, int, int]:
    """ Get the range of front pages that need to be scraped for usernames
    based on a range of rankings to be scraped.

    :param start_rank: lowest player ranking to include in scraping
    :param end_rank: highest player ranking to include in scraping
    :return: tuple of
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

    firstpage = (start_rank - 1) // 25 + 1  # first page containing rankings within range
    lastpage = (end_rank - 1) // 25 + 1     # last page containing rankings within range
    startind = (start_rank - 1) % 25        # index of first row in first page to start taking from
    endind = (end_rank - 1) % 25 + 1        # index of last row in last page to keep

    return firstpage, startind, lastpage, endind


def mongodoc_to_player(doc: Dict[str, Any]) -> PlayerRecord:
    return PlayerRecord(
        ts=doc['ts'],
        rank=doc['rank'],
        username=doc['username'],
        total_level=doc['total_level'],
        total_xp=doc['total_xp'],
        stats=doc['stats']
    )


def player_to_mongodoc(record: PlayerRecord) -> Dict[str, Any]:
    return dataclasses.asdict(record)
