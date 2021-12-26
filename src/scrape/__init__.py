import asyncio

import aiohttp
import numpy as np
from bs4 import BeautifulSoup


class ApiError(Exception):
    pass


def repeat_shuffled(items):
    while True:
        yield from np.random.permutation(items)


async def run_subprocess(command):
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()
    if stderr:
        raise ValueError("could not run '{}': {}".format(command, stderr.decode('utf-8')))

    return stdout.decode('utf-8')


async def pull_hiscores_page(session, page_num, max_attempts=5):
    try:
        for _ in range(max_attempts):

                async with session.get(
                    'https://secure.runescape.com/m=hiscore_oldschool/overall',
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
            raise ApiError("could not get page after {} tries: {}".format(max_attempts, error))

    except asyncio.TimeoutError as e:
        raise KeyError("hiscores page {} unavailable: {}".format(page_num, e))
    except aiohttp.ClientError as e:
        raise ApiError("could not pull hiscores page {}: {}".format(page_num, e))


def parse_hiscores_page(page_html):

    # Extract 25 usernames and overall rank/total level/xp from the raw HTML.
    soup = BeautifulSoup(page_html, 'html.parser')
    page_body = soup.html.body
    try:
        main_div = page_body.find_all('div')[4]
        hiscores_div = main_div.find_all('div')[7]
        stats_table = hiscores_div.find_all('div')[4]
        personal_hiscores = stats_table.div.find_all('div')[1]
        table_rows = personal_hiscores.div.table.tbody
        player_rows = table_rows.find_all('tr')[1:]
    except IndexError as e:
        raise ApiError("could not parse page body:\n{}".format(page_body))

    ranks = []
    usernames = []
    for row in player_rows:
        try:
            rank, username = row.find_all('td')[:2]
        except IndexError as e:
            raise ApiError("could not parse page row: {}".format(e))

        rank = int(rank.string.strip().replace(',', ''))
        ranks.append(rank)

        username = username.a.string.replace('\xa0', ' ')
        usernames.append(username)

    return ranks, usernames


async def pull_player_stats(session, username, max_attempts=5):

    try:
        for _ in range(max_attempts):
            async with session.get(
                'http://services.runescape.com/m=hiscore_oldschool/index_lite.ws',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'
                },
                params={
                    'player': username
                }
            ) as response:
                if response.status == 404:
                    raise KeyError("user '{}' not found".format(username))
                elif response.status != 200:
                    continue

                csv = await response.text()
                csv = csv.strip().replace('\n', ',')
                csv = username + ',' + csv
                return csv
        else:
            error = await response.text()
            raise ApiError("could not get page after {} tries: {}".format(max_attempts, error))

    except TimeoutError as e:
        raise KeyError("data for '{}' unavailable: {}".format(username, e))
    except aiohttp.ClientError as e:
        raise ApiError("could not pull player stats: {}".format(e))
    except aiohttp.ClientConnectionError as e:
        raise ApiError("could not pull player stats: {}".format(e))
