import asyncio
import dataclasses
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict, Tuple

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError, ClientOSError
from bs4 import BeautifulSoup

from src.common import osrs_csv_api_stats


@dataclass(order=True)
class PageJob:
    """ Represents a page to be queried from the OSRS hiscores. """
    pagenum: int                                     # page on the OSRS hiscores (between 1 and 80000)
    startind: int = field(default=0, compare=False)  # start index of the usernames wanted from this page
    endind: int = field(default=25, compare=False)   # end index of the usernames wanted from this page


@dataclass(order=True)
class UsernameJob:
    """ Represents a username to be queried for account stats. """
    rank: int
    username: str = field(compare=False)


@dataclass(order=True)
class PlayerRecord:
    """ Represents a player data record scraped from the hiscores. """
    rank: int
    total_level: int
    total_xp: int
    ts: datetime  # time record was scraped
    username: str = field(compare=False)
    stats: List[int] = field(compare=False)


class RequestFailed(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg


class UserNotFound(Exception):
    pass


class IPAddressBlocked(Exception):
    pass


class ParsingFailed(Exception):
    pass


async def get_hiscores_page(sess: ClientSession, page_num: int) -> Tuple[List[int], List[str]]:
    """ Fetch a front page of the OSRS hiscores by page number.

    Raises:
        IPAddressBlocked if client has been blocked by hiscores server
        RequestFailed if page could not be downloaded for some other reason
        ParsingFailed if downloaded page HTML could not be correctly parsed

    :param session: HTTP client session
    :param page_num: integer between 1 and 80000
    :return:
        - list of the 25 rank numbers on one page of the hiscores
        - list of the 25 usernames corresponding to those ranks
    """
    url = "https://secure.runescape.com/m=hiscore_oldschool/overall"
    params = {'table': 0, 'page': page_num}
    page_html = await http_request(sess, url, params, timeout=10)
    return parse_hiscores_page(page_html)


async def get_player_stats(sess: ClientSession, username: str) -> PlayerRecord:
    """ Fetch stats for a player by username.

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
    try:
        stats_csv = await http_request(sess, url, params)
    except RequestFailed as e:
        if e.code == 404:
            raise UserNotFound(username)
        raise
    return parse_stats_csv(username, stats_csv)


async def http_request(sess: ClientSession, server_url: str, query_params: Dict[str, Any], timeout: int = None):
    headers = {"Access-Control-Allow-Origin": "*",
               "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept"}
    try:
        async with sess.get(server_url, headers=headers, params=query_params, timeout=timeout) as resp:
            if resp.status == 503:
                raise IPAddressBlocked("server too busy")
            elif resp.status != 200:
                try:
                    error = await resp.text()
                except ClientConnectionError as e:
                    raise IPAddressBlocked(f"client connection error: {e}")
                raise RequestFailed(resp.status, error)
            return await resp.text()
    except asyncio.TimeoutError:
        raise IPAddressBlocked(f"timed out while trying to connect")
    except ClientOSError as e:
        raise IPAddressBlocked(f"client OS error: {e}")


def parse_hiscores_page(page_html: str) -> Tuple[List[int], List[str]]:
    page_text = BeautifulSoup(page_html, 'html.parser').text

    table_start = page_text.find('Overall\nHiscores')
    table_end = page_text.find('Search by name')
    if table_start == -1 or table_end == -1:
        if "your IP has been temporarily blocked" in page_text:
            raise IPAddressBlocked("blocked temporarily due to high usage")
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
    return ranks, unames


_rank_col = osrs_csv_api_stats().index('total_rank')
_tlvl_col = osrs_csv_api_stats().index('total_level')
_txp_col = osrs_csv_api_stats().index('total_xp')

def parse_stats_csv(username: str, raw_csv: str) -> PlayerRecord:
    stats_csv = raw_csv.strip().replace('\n', ',')  # stat groups are separated by newlines
    stats = [int(i) for i in stats_csv.split(',')]
    stats = [None if i < 0 else i for i in stats]
    assert len(stats) == len(osrs_csv_api_stats()), f"the API returned an unexpected number of stats: {stats}"

    ts = datetime.utcnow()
    ts = ts.replace(microsecond=ts.microsecond - ts.microsecond % 1000)  # mongo only has millisecond precision
    return PlayerRecord(
        username=username,
        rank=stats[_rank_col],
        total_level=stats[_tlvl_col],
        total_xp=stats[_txp_col],
        stats=stats,
        ts = ts
    )


def get_page_range(start_rank: int, end_rank: int) -> Tuple[int, int, int, int]:
    """
    todo: write docstring
    :param start_rank:
    :param end_rank:
    :return:
    """
    if start_rank > end_rank:
        raise ValueError(f"start rank ({start_rank}) cannot be greater than end rank ({end_rank})")
    firstpage = (start_rank - 1) // 25 + 1  # first page containing rankings within range
    lastpage = (end_rank - 1) // 25 + 1     # last page containing rankings within range
    startind = (start_rank - 1) % 25        # index of first row in first page to start taking from
    endind = (end_rank - 1) % 25 + 1        # index of last row in last page to keep
    return firstpage, startind, lastpage, endind


def reset_vpn(ntries=3):
    vpn_script = Path(__file__).resolve().parents[2] / "bin" / "reset_vpn"
    for n in range(1, ntries + 1):
        try:
            subprocess.run(vpn_script).check_returncode()
            break
        except subprocess.CalledProcessError as e:
            if n == ntries:
                raise RuntimeError(f"error resetting VPN: {e.returncode}, stdout: {e.stdout}, stderr: {e.stderr}")
            print("failed to reset VPN. Trying again in 5 seconds...")
            time.sleep(5)


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
