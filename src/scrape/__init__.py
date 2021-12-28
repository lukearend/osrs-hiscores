import requests
from bs4 import BeautifulSoup


async def request_page(session, page_num, max_attempts=5):
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


def parse_page(page_html):
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
        raise ValueError("could not parse page body:\n{}".format(page_body))

    result = {}
    for row in player_rows:
        try:
            rank, username, total_level = row.find_all('td')[:3]
        except IndexError as e:
            raise ValueError("could not parse row: {}".format(e))

        rank = int(rank.string.strip().replace(',', ''))
        username = username.a.string.replace('\xa0', ' ')
        total_level = int(total_level.string.strip().replace(',', ''))

        result[rank] = {
            'username': username,
            'total_level': total_level
        }

    return result


async def request_stats(session, username, max_attempts=5):
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
            csv = '{},{}'.format(username, csv)
            return csv

    else:
        error = await response.text()
        raise ApiError("could not get page after {} tries: {}".format(max_attempts, error))
