import asyncio

import aiohttp
import numpy as np
from bs4 import BeautifulSoup


def repeat_shuffled(batch):
    while True:
        yield from np.random.permutation(batch)


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
        raise ValueError("could not get page after {} tries: {}".format(max_attempts, error))


def parse_hiscores_page(page_html):

    # Extract 25 usernames and overall rank/total level/xp from the raw HTML.
    soup = BeautifulSoup(page_html, 'html.parser')
    try:
        page_rows = soup.html.body
        main_div = page_rows.find_all('div')[4]
        hiscores_div = main_div.find_all('div')[7]
        stats_table = hiscores_div.find_all('div')[4]
        personal_hiscores = stats_table.div.find_all('div')[1]
        table_rows = personal_hiscores.div.table.tbody
        player_rows = table_rows.find_all('tr')[1:]
    except IndexError as e:
        raise ValueError("could not parse page: {}".format(e))

    results = []
    for row in player_rows:
        try:
            rank, username, total_level = row.find_all('td')[:3]
        except IndexError as e:
            raise ValueError("could not parse row: {}".format(e))

        rank = int(rank.string.strip().replace(',', ''))
        username = username.a.string.replace('\xa0', ' ')
        total_level = int(total_level.string.strip().replace(',', ''))

        results.append({
            'rank': rank,
            'username': username,
            'total_level': total_level
        })

    return results


async def request_player_stats(username, max_attempts=5):
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
            csv = stats_csv.replace('\n', ',')
            csv = username + ',' + csv
            return csv

    else:
        error = await response.text()
        raise ValueError("could not get page after {} tries: {}".format(max_attempts, error))
