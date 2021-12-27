import requests
from bs4 import BeautifulSoup


def request_page(page_number, max_attempts=5):
    if page_number < 1 or page_number > 80000:
        raise ValueError("page number must be between 1 and 80000 inclusive")

    for attempt in range(max_attempts):
        response = requests.get(
            'https://secure.runescape.com/m=hiscore_oldschool/overall',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'
            },
            params={
                'table': 0,
                'page': page_number
            }
        )

        if response.status_code == 200:
            break
        else:
            continue
    else:
        raise ValueError("max attempts exceeded, could not get page after {} tries"
                         .format(max_attempts))

    return response.text


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
        raise ApiError("could not parse page body:\n{}".format(page_body))

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


def request_stats(username, max_attempts=5):
    for attempt in range(max_attempts):
        response = requests.get(
            'http://services.runescape.com/m=hiscore_oldschool/index_lite.ws',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept'
            },
            params={
                'player': username
            }
        )

        if response.status_code == 200:
            break
        elif response.status_code == 404:
            raise KeyError("user '{}' not found".format(username))
    else:
        raise ValueError("max attempts exceeded, could not get page after {} tries"
                         .format(max_attempts))

    result = response.text.replace('\n', ',')
    result = "{},".format(username) + result
    return result
