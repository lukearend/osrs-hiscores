import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import List, Any, Dict

from bs4 import BeautifulSoup

from src.common import osrs_csv_api_stats


REQUEST_MAX_ATTEMPTS = 5

class PageRequestFailed(Exception): pass

class PageParseError(Exception): pass

class UserRequestFailed(Exception): pass

class UserNotFound(Exception): pass


@dataclass
class PlayerRecord:
    """ Represents a player data record scraped from the hiscores. """
    ts: datetime  # time scraped
    rank: int
    username: str
    total_level: int
    total_xp: int
    stats: List[int]


async def get_page_usernames(session, page_num: int) -> List[str]:
    """
    Fetch a front page of the OSRS hiscores by page number.

    :param session: HTTP client session
    :param page_num: integer between 1 and 80000
    :return: list of the usernames on one page of the hiscores
    """
    page_html = await request_hiscores_page(session, page_num)
    return parse_page_usernames(page_html)


async def get_player_stats(session, username) -> PlayerRecord:
    """
    Fetch stats for a player by username.

    :param session: HTTP client session
    :param username: username for player to fetch
    :return: object containing player stats data
    """
    stats_csv = await request_player_stats(session, username)
    return parse_stats_csv(username, stats_csv)


_http_headers = {"Access-Control-Allow-Origin": "*",
                 "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept"}

async def request_hiscores_page(session, page_num) -> str:
    for _ in range(REQUEST_MAX_ATTEMPTS):
        async with session.get("https://secure.runescape.com/m=hiscore_oldschool/overall",
                               headers=_http_headers,
                               params={'table': 0, 'page': page_num}) as response:
            if response.status != 200:
                continue
            return await response.text()
    else:
        error = await response.text()
        raise PageRequestFailed(f"could not get page after {REQUEST_MAX_ATTEMPTS} tries: {error}")


def parse_page_usernames(page_html: str) -> List[str]:
    try:
        soup = BeautifulSoup(page_html, 'html.parser')
        page_body = soup.html.body
        main_div = page_body.find_all('div')[4]
        hiscores_div = main_div.find_all('div')[7]
        stats_table = hiscores_div.find_all('div')[4]
        personal_hiscores = stats_table.div.find_all('div')[1]
        table_rows = personal_hiscores.div.table.tbody
        player_rows = table_rows.find_all('tr')[1:]
        usernames = []

        for row in player_rows:
            username = row.find_all('td')[1]
            username = username.a.string.replace('\xa0', ' ')
            usernames.append(username)

    except IndexError as e:
        raise PageParseError(f"failed while parsing page: {e}")

    return usernames


async def request_player_stats(session, username) -> str:
    for _ in range(REQUEST_MAX_ATTEMPTS):
        async with session.get("http://services.runescape.com/m=hiscore_oldschool/index_lite.ws",
                               headers=_http_headers,
                               params={'player': username}) as response:
            if response.status == 404:
                raise UserNotFound(username)
            elif response.status != 200:
                continue
            return await response.text()
    else:
        error = await response.text()
        raise UserRequestFailed(f"could not get player '{username}' after {REQUEST_MAX_ATTEMPTS} tries: {error}")


_rank_col = osrs_csv_api_stats().index('total_rank')
_tlvl_col = osrs_csv_api_stats().index('total_level')
_txp_col = osrs_csv_api_stats().index('total_xp')

def parse_stats_csv(username, raw_csv: str) -> PlayerRecord:
    stats_csv = raw_csv.strip().replace('\n', ',')  # stat groups are separated by newlines
    stats = [int(i) for i in stats_csv.split(',')]
    stats = [None if i < 0 else i for i in stats]
    assert len(stats) == len(osrs_csv_api_stats()), (
        "the CSV API returned an unexpected number of stats (was a new skill or activity recently added?)")

    ts = datetime.utcnow()
    ts = ts.replace(microsecond=ts.microsecond - ts.microsecond % 1000)  # mongo only has millisecond precision
    return PlayerRecord(
        ts=ts,
        rank=stats[_rank_col],
        username=username,
        total_level=stats[_tlvl_col],
        total_xp=stats[_txp_col],
        stats=stats
    )


def mongodoc_to_player(doc) -> PlayerRecord:
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
