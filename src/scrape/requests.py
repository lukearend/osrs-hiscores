""" Code that makes requests to the OSRS hiscores. """

from asyncio import TimeoutError
from datetime import datetime
from typing import List, Tuple, Dict

from aiohttp import ClientSession, ClientConnectionError
from bs4 import BeautifulSoup

from src.scrape import PlayerRecord, RequestFailed, UserNotFound, ServerBusy, csv_api_stats


class ParsingFailed(Exception):
    """ Raised when data received from the hiscores API could not be parsed. """


async def get_hiscores_page(sess: ClientSession, page_num: int) -> List[Tuple[int, str]]:
    """ Fetch a front page of the OSRS hiscores by page number. The
    "front pages" are the 80000 pages containing ranks for the top 2
    million players. Each page provides 25 rank/username pairs, such
    that page 1 contains ranks 1-25, page 2 contains ranks 26-50, etc.

    Raises:
        RequestFailed if page could not be downloaded from hiscores server

    :param sess: HTTP client session
    :param page_num: integer between 1 and 80000
    :return: list of the 25 rank/username pairs from one page of the hiscores
    """
    if page_num > 80000:
        raise ValueError("page number cannot be greater than 80000")

    url = "https://secure.runescape.com/m=hiscore_oldschool/overall"
    try:
        page_html = await http_request(sess, url, params={'table': 0, 'page': page_num})
    except (TimeoutError, RequestFailed) as e:
        raise RequestFailed(f"page {page_num}: {e}")
    return parse_hiscores_page(page_html)


async def get_player_stats(sess: ClientSession, username: str) -> PlayerRecord:
    """ Fetch stats for a player by username. A description of
    the result format for the OSRS Hiscores API is available at
    https://runescape.wiki/w/Application_programming_interface.

    Raises:
        UserNotFound if the requested user doesn't exist
        TimeoutError if request for user record timed out
        RequestFailed if user data could not be fetched for some other reason

    :param sess: HTTP client session
    :param username: username for player to fetch
    :return: object containing player stats data
    """
    url = "https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws"
    try:
        stats_csv = await http_request(sess, url, params={'player': username})
    except TimeoutError as e:
        raise ServerBusy(e)
    except RequestFailed as e:
        raise UserNotFound({username}) if e.code == 404 else e
    return parse_stats_csv(username, stats_csv)


async def http_request(sess: ClientSession, url: str, params: Dict[str, str]):
    """ Make an HTTP request and handle any failure that occurs. """

    headers = {"Access-Control-Allow-Origin": "*",
               "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept"}
    try:
        async with sess.get(url, headers=headers, params=params, timeout=30) as resp:
            text = await resp.text()
            if resp.status == 200:
                return text
            raise RequestFailed(text, code=resp.status)
    except TimeoutError:
        raise TimeoutError(f"timed out")
    except ClientConnectionError as e:
        raise RequestFailed(f"client connection error: {e}")


def parse_hiscores_page(page_html: str) -> List[Tuple[int, str]]:
    """ Extract a list of ranks and usernames from a front page of the hiscores. """

    page_text = BeautifulSoup(page_html, 'html.parser').text
    table_start = page_text.find('Overall\nHiscores')
    table_end = page_text.find('Search by name')
    if table_start == -1 or table_end == -1:
        if "your IP has been temporarily blocked" in page_text:
            raise RequestFailed("blocked temporarily due to high usage")
        raise ParsingFailed(f"could not find main rankings table. Page text: {page_text}")

    table_raw = page_text[table_start:table_end]
    table_flat = [s for s in table_raw.split('\n') if s]  # all items comprising the page's hiscores table
    assert table_flat[:5] == ['Overall', 'Hiscores', 'Rank', 'Name', 'LevelXP'], (
        f"unexpected HTML formatting for the main rankings table. Page text: {page_text}")
    table_flat = table_flat[5:]  # remove front matter from table

    # The table contains rank, name, total_level, xp for each of 25 players.
    assert len(table_flat) == 100, f"unexpected number of items in main rankings table. Items:\n{table_flat}"
    ranks = [int(n.replace(',', '')) for n in table_flat[::4]]
    unames = table_flat[1::4]
    unames = [s.replace('\xa0', ' ') for s in unames]  # some usernames contain hex char A0, "non-breaking space"
    return list(zip(ranks, unames))


def parse_stats_csv(username: str, raw_csv: str) -> PlayerRecord:
    """ Transform raw CSV data for a player into a normalized data record. """

    # The CSV data returned is groups of (rank, xp, level) for each stat and groups of
    # (rank, score) for each boss/activity, with the groups separated by newlines.
    stats = []
    for stat_group in raw_csv.strip().split('\n'):
        stat_group = [int(n) for n in stat_group.split(',')]

        # If skill data is missing (unranked), CSV API returns -1, 1, -1 for rank, level, xp.
        # Change level to -1 so as not to imply the skill is actually level 1.
        if len(stat_group) == 3 and stat_group[0] < 0 and stat_group[2] < 0:
            stat_group[1] = -1

        for n in stat_group:
            stats.append(n)

    assert len(stats) == len(csv_api_stats()), f"the API returned an unexpected number of stats: {stats}"
    return PlayerRecord(username=username, stats=stats, ts=datetime.utcnow())
