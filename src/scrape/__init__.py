import asyncio
import dataclasses
import logging
import shlex
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from getpass import getpass
from pathlib import Path
from subprocess import Popen, PIPE, DEVNULL
from typing import List, Any, Dict, Tuple

from aiohttp import ClientSession, ClientConnectionError
from bs4 import BeautifulSoup

from src.common import osrs_csv_api_stats


class JobQueue:
    """ A priority queue that allows to set a maxsize with a soft limit. Calling put()
    with force=False is subject to blocking if queue is full; calling with force=True
    will immediately force an item into the queue no matter its size. """

    def __init__(self, maxsize=None):
        self.q = asyncio.PriorityQueue()
        self.shortened = asyncio.Event()
        self.maxsize = maxsize

    async def put(self, item, force=False):
        if self.maxsize and not force:
            while self.q.qsize() >= self.maxsize:
                await self.shortened.wait()
                self.shortened.clear()

        await self.q.put(item)

    async def get(self):
        item = await self.q.get()
        self.shortened.set()
        return item

    async def join(self):
        await self.q.join()

    def task_done(self, n=1):
        for _ in range(n):
            self.q.task_done()

    def qsize(self):
        return self.q.qsize()


@dataclass(order=True)
class PlayerRecord:
    """ Represents data for one player scraped from the hiscores. """
    rank: int
    username: str = field(default=None, compare=False)
    total_level: int = field(default=None, compare=False)
    total_xp: int = field(default=None, compare=False)
    stats: List[int] = field(default=None, compare=False)
    ts: datetime = field(default=None, compare=False)          # time at which record was scraped

    def __str__(self):
        return f"PlayerRecord({self.rank}, '{self.username}')"


@dataclass(order=True)
class PageJob:
    """ Represents the following task: fetch a front page from the OSRS hiscores,
    extract the rank/username data, and enqueue the 25 usernames in rank order. """
    pagenum: int                                               # page # on the front pages (between 1 and 80000)
    startind: int = field(default=0, compare=False)            # start index of the usernames wanted from this page
    endind: int = field(default=25, compare=False)             # end index of the usernames wanted from this page
    pagecontents: Any = field(default=None, compare=False)     # page results, kept as partial progress when cancelled

    def __str__(self):
        return f"PageJob({self.pagenum}, {self.startind}, {self.endind}, hascontents: {self.pagecontents})"


@dataclass(order=True)
class UsernameJob:
    """ Represents the task of fetching account stats by username and enqueueing
    the stats alongside other workers in a way that preserves rank order. """
    rank: int
    username: str = field(compare=False)
    result: PlayerRecord = field(default=None, compare=False)  # downloaded stats, kept as progress when cancelled

    def __str__(self):
        return f"UsernameJob({self.rank}, '{self.username}')"


class RequestFailed(Exception):
    """ Raised when a request to the hiscores API fails. """
    def __init__(self, message, code=None):
        prefix = f"{code}: " if code is not None else ''
        super().__init__(f"{prefix}{message}")
        self.code = code


class UserNotFound(Exception):
    """ Raised when data for a requested username does not exist. """
    pass


class ParsingFailed(Exception):
    """ Raised when data fails to parse correctly. If this is raised, it means
    the hiscores API returned something the parsing code has not correctly
    accounted for. This might happen if the hiscores API changes (e.g. by
    adding a new skill or activity) and would indicate the parsing function
    needs to be patched.
    """
    pass


async def get_hiscores_page(sess: ClientSession, page_num: int) -> Tuple[List[int], List[str]]:
    """ Fetch a front page of the OSRS hiscores by page number. The "front pages"
    are the 80000 pages containing ranks for the top 2 million players. Each page
    provides 25 rank/username pairs, such that page 1 contains ranks 1-25, page
    2 contains ranks 26-50, etc.

    Raises:
        RequestFailed if page could not be downloaded from hiscores server
        ParsingFailed if downloaded page HTML could not be correctly parsed

    :param session: HTTP client session
    :param page_num: integer between 1 and 80000
    :return:
        - list of the 25 rank numbers on one page of the hiscores
        - list of the 25 usernames corresponding to those ranks
    """
    if page_num > 80000:
        raise ValueError("page number cannot be greater than 80000")

    url = "https://secure.runescape.com/m=hiscore_oldschool/overall"
    params = {'table': 0, 'page': page_num}
    try:
        page_html = await http_request(sess, url, params, timeout=10)
    except asyncio.TimeoutError:
        # If a page request times out, it is because we are blocked by the remote server.
        raise RequestFailed(f"timed out while trying to get page")
    return parse_hiscores_page(page_html)


async def get_player_stats(sess: ClientSession, username: str) -> PlayerRecord:
    """ Fetch stats for a player by username.

    Raises:
        UserNotFound if request for user record timed out or user doesn't exist
        RequestFailed if user data could not be fetched for some other reason
        ParsingFailed if the data received does not match the expected format

    :param session: HTTP client session
    :param username: username for player to fetch
    :return: object containing player stats data
    """
    url = "http://services.runescape.com/m=hiscore_oldschool/index_lite.ws"
    params = {'player': username}
    try:
        stats_csv = await http_request(sess, url, params, timeout=15)
    except asyncio.TimeoutError:
        # Not all players are fetched from the CSV API in an equal amount of time.
        # If it's taking way too long (i.e. many seconds) we count the user as missing.
        raise UserNotFound(f"'{username}', request timed out")
    except RequestFailed as e:
        raise UserNotFound(f"'{username}', 404 response") if e.code == 404 else e
    return parse_stats_csv(username, stats_csv)


async def http_request(sess: ClientSession, server_url: str, query_params: Dict[str, Any], timeout: int = None):
    """ Make an HTTP request and handle any failure that occurs. """
    headers = {"Access-Control-Allow-Origin": "*",
               "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept"}
    try:
        async with sess.get(server_url, headers=headers, params=query_params, timeout=timeout) as resp:
            text = await resp.text()
            if resp.status == 200:
                return text
            raise RequestFailed(text, code=resp.status)
    except ClientConnectionError as e:
        raise RequestFailed(f"client connection error: {e}")


def parse_hiscores_page(page_html: str) -> Tuple[List[int], List[str]]:
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
    return ranks, unames


_rank_col = osrs_csv_api_stats().index('total_rank')
_tlvl_col = osrs_csv_api_stats().index('total_level')
_txp_col = osrs_csv_api_stats().index('total_xp')

def parse_stats_csv(username: str, raw_csv: str) -> PlayerRecord:
    """ Transform raw CSV data for a player into a normalized data record. """
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


def reset_vpn():
    """ Reset VPN, acquiring a new IP address. Requires root permissions. """
    vpn_script = Path(__file__).resolve().parents[2] / "bin" / "reset_vpn"
    p = subprocess.run(vpn_script)
    p.check_returncode()


def getsudo(password):
    """ Attempt to acquire sudo permissions using the given password. """
    proc = Popen(shlex.split(f"sudo -Svp ''"), stdin=PIPE, stderr=DEVNULL)
    proc.communicate(password.encode())
    return True if proc.returncode == 0 else False


def askpass():
    """ Request root password for VPN usage. """
    msg1 = textwrap.dedent("""
        Root permissions are required by the OpenVPN client which is used during
        scraping to periodically acquire a new IP address. Privileges granted here
        will only be used to manage the VPN connection and the password will only
        persist in RAM as long as the program is running.
        """)

    msg2 = textwrap.dedent("""
        Proceeding without VPN. It is likely your IP address will get blocked or
        throttled after a few minutes of scraping due to the volume of requests.
        """)

    print(msg1)
    pwd = getpass("Enter root password (leave empty to continue without VPN): ")
    if not pwd:
        print(msg2)
        return None
    print()
    return pwd


def print_and_log(msg, level):
    print(msg)
    logger = getattr(logging, level.lower())
    logger(msg)


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
