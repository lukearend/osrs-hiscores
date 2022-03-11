import asyncio
from collections import namedtuple
from dataclasses import dataclass
from typing import List

import aiohttp
from bs4 import BeautifulSoup

from src.common import osrs_skills, osrs_minigames

REQUEST_MAX_ATTEMPTS = 5


class PageParseError(Exception): pass
class HiscoresApiError(Exception): pass
class UserNotFound(Exception): pass


@dataclass
class RankData:
    """ Represents a row on the overall ranking pages of the OSRS hiscores. """
    rank: int
    username: str
    total_level: int
    total_xp: int


def parse_page_html(page_html: str) -> List[RankData]:
    """
    Parse username info out of the raw HTML for a front page of the OSRS hiscores.

    :param page_html: raw HTML for an OSRS hiscores page
    :return: dictionary mapping the rank for each player found on the page
             to username and total level for that player.
    """
    soup = BeautifulSoup(page_html, 'html.parser')
    try:
        page_body = soup.html.body
        main_div = page_body.find_all('div')[4]
        hiscores_div = main_div.find_all('div')[7]
        stats_table = hiscores_div.find_all('div')[4]
        personal_hiscores = stats_table.div.find_all('div')[1]
        table_rows = personal_hiscores.div.table.tbody
        player_rows = table_rows.find_all('tr')[1:]
    except IndexError as e:
        raise PageParseError(f"could not parse page body:\n{page_body}")

    page_rows = []
    for row in player_rows:
        try:
            rank, username, total, xp = row.find_all('td')[:4]
        except IndexError as e:
            raise PageParseError("could not parse row: {}".format(e))

        rank = int(rank.string.strip().replace(',', ''))
        username = username.a.string.replace('\xa0', ' ')
        total = int(total.string.strip().replace(',', ''))
        xp = int(xp.string.strip().replace(',', ''))

        player_data = RankData(rank=rank, username=username, total_level=total, total_xp=xp)
        page_rows.append(player_data)

    return page_rows


async def request_hiscores_page(session, page_num) -> str:
    for _ in range(REQUEST_MAX_ATTEMPTS):
        async with session.get(
            "https://secure.runescape.com/m=hiscore_oldschool/overall",
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'
            },
            params={
                'table': 0,
                'page': page_num
            }
        ) as response:
            if response.status != 200:
                continue
            return await response.text()

    else:
        error = await response.text()
        raise HiscoresApiError(f"could not get page after {REQUEST_MAX_ATTEMPTS} tries: {error}")


async def get_hiscores_page(session, page_num: int) -> List[RankData]:
    """
    Fetch a front page of the OSRS hiscores by page number.

    :param session: HTTP client session
    :param page_num: integer between 1 and 80000
    :return: list of player rankings from one page of the hiscores
    """
    page_html = await request_hiscores_page(session, page_num)
    return parse_page_html(page_html)


SkillStats = namedtuple('SkillStats', osrs_skills())
MinigameStats = namedtuple('MinigameStats', osrs_minigames())

@dataclass
class PlayerData:
    rank: int
    username: str
    total_level: int
    total_xp: int
    skill_ranks: SkillStats
    skill_levels: SkillStats
    skill_xp: SkillStats
    minigame_ranks: MinigameStats
    minigame_scores: MinigameStats


def parse_stats_csv(stats_csv: str) -> PlayerData:
    pass


async def get_player_stats(session, username) -> PlayerData:
    stats_csv = await request_player_stats(session, username)
    return parse_stats_csv(stats_csv)


async def request_player_stats(session, username) -> str:
    """
    Fetch stats for a player from the OSRS hiscores.

    :param session: HTTP client session
    :param username: username for player to fetch
    :return: player stats as
    """
    for _ in range(REQUEST_MAX_ATTEMPTS):
        async with session.get(
            "http://services.runescape.com/m=hiscore_oldschool/index_lite.ws",
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'
            },
            params={
                'player': username
            }
        ) as response:
            if response.status == 404:
                raise UserNotFound(username)
            elif response.status != 200:
                continue

            # Stats arrive as CSV series of rank,level,xp for each skill.
            # Order of skills is same as given in osrs_skills.json reference file.
            csv = await response.text()
            csv = csv.strip().replace('\n', ',')
            csv = f"{username},{csv}"
            return csv

    else:
        error = await response.text()
        raise HiscoresApiError(f"could not get page after {REQUEST_MAX_ATTEMPTS} tries: {error}")


async def run_workers(workerfn: Callable, jobs: Iterable[Any], out_file: str, pbar: tqdm, nworkers: int):
    """
    Launch a set of workers to perform data scraping.

    :param workerfn: Each worker invokes this function to process jobs.
    :param jobs: An iterable of jobs to be processed by workers.
    :param out_file: CSV file to which results are appended.
    :param pbar: tqdm object representing total progress (is updated by workers)
    :param nworkers: number of workers to run
    """
    file_lock = asyncio.Lock()
    job_queue = asyncio.Queue()
    for job in jobs:
        job_queue.put_nowait(job)

    async with aiohttp.ClientSession() as sess:
        workers = []
        for i in range(nworkers):
            workers.append(asyncio.create_task(
                workerfn(sess, job_queue, out_file, file_lock, pbar)
            ))
            await asyncio.sleep(0.1)

        await asyncio.gather(*workers)
