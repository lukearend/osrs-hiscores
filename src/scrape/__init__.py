import asyncio
import dataclasses
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Any, Dict

from aiohttp.client_exceptions import ClientConnectionError, ClientOSError
from bs4 import BeautifulSoup

from src.common import osrs_csv_api_stats


class IPAddressBlocked(Exception):
    pass


class UserNotFound(Exception):
    pass


class RequestFailed(Exception):
    pass


class ParsingFailed(Exception):
    pass


@dataclass(order=True)
class PlayerRecord:
    """ Represents a player data record scraped from the hiscores. """
    rank: int
    total_level: int
    total_xp: int
    username: str
    stats: List[int]
    ts: datetime  # time scraped


async def get_page_usernames(sess, page_num: int) -> List[str]:
    """
    Fetch a front page of the OSRS hiscores by page number.

    Raises:
        IPAddressBlocked if client has been blocked by hiscores server
        RequestFailed if page could not be downloaded for some other reason
        ParsingFailed if downloaded page HTML could not be correctly parsed

    :param session: HTTP client session
    :param page_num: integer between 1 and 80000
    :return: list of the usernames on one page of the hiscores
    """
    url = "https://secure.runescape.com/m=hiscore_oldschool/overall"
    params = {'table': 0, 'page': page_num}
    page_html = await http_request(sess, url, params, request_type='page')
    return parse_page_usernames(page_html)


async def get_player_stats(sess, username) -> PlayerRecord:
    """
    Fetch stats for a player by username.

    Raises:
        IPAddressBlocked if client has been blocked by hiscores server
        UserNotFound if data could not be fetched because user does not exist
        RequestFailed if user data could not be fetched for some other reason
        ParsingFailed if the expected format does not match the data received

    :param session: HTTP client session
    :param username: username for player to fetch
    :return: object containing player stats data
    """
    url = "http://services.runescape.com/m=hiscore_oldschool/index_lite.ws"
    params = {'player': username}
    stats_csv = await http_request(sess, url, params, request_type='stats')
    return parse_stats_csv(username, stats_csv)


async def http_request(sess, server_url: str, query_params: Dict[str, Any], request_type: str):
    headers = {"Access-Control-Allow-Origin": "*",
               "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept"}
    try:
        async with sess.get(server_url, headers=headers, params=query_params) as resp:
            if resp.status == 404:
                assert request_type == 'stats', "404 responses are only expected from the stats CSV API"
                raise UserNotFound(query_params['player'])
            elif resp.status == 503:
                raise IPAddressBlocked("server too busy")
            elif resp.status != 200:
                try:
                    error = await resp.text()
                except ClientConnectionError:
                    raise IPAddressBlocked("server blocked connection")
                raise RequestFailed(f"{resp.status}: {error}")
            return await resp.text()
    except ClientOSError:
        raise IPAddressBlocked("timed out while trying to connect to server")


def parse_page_usernames(page_html: str) -> List[str]:
    soup = BeautifulSoup(page_html, 'html.parser')
    try:
        main_div = soup.html.body.find_all('div')[4]
        center_div = main_div.find_all('div')[7]
        stats_table = center_div.find_all('div')[4]
        personal_hiscores = stats_table.div.find_all('div')[1]
        player_rows = personal_hiscores.div.table.tbody.find_all('tr')[1:]
        usernames = []
        for row in player_rows:
            username = row.find_all('td')[1]
            username = username.a.string.replace('\xa0', ' ')
            usernames.append(username)
    except IndexError as e:
        for p in soup.html.body.find_all():
            if p.string and re.match(p.string.lower(), "your ip has been [a-z ]* blocked"):
                raise IPAddressBlocked(p.string)
        raise ParsingFailed(f"failed to parse page: {e}. html:\n\n{page_html}")
    return usernames


_rank_col = osrs_csv_api_stats().index('total_rank')
_tlvl_col = osrs_csv_api_stats().index('total_level')
_txp_col = osrs_csv_api_stats().index('total_xp')

def parse_stats_csv(username: str, raw_csv: str) -> PlayerRecord:
    stats_csv = raw_csv.strip().replace('\n', ',')  # stat groups are separated by newlines
    stats = [int(i) for i in stats_csv.split(',')]
    stats = [None if i < 0 else i for i in stats]
    if len(stats) != len(osrs_csv_api_stats()):
        raise ParsingFailed("the CSV API returned an unexpected number of stat columns")

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


def mongodoc_to_playerrecord(doc: Dict[str, Any]) -> PlayerRecord:
    return PlayerRecord(
        ts=doc['ts'],
        rank=doc['rank'],
        username=doc['username'],
        total_level=doc['total_level'],
        total_xp=doc['total_xp'],
        stats=doc['stats']
    )


def playerrecord_to_mongodoc(record: PlayerRecord) -> Dict[str, Any]:
    return dataclasses.asdict(record)
