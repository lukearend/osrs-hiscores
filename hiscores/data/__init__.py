import pathlib
import pickle

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from scipy.stats import pearsonr


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


def parse_page(page_text):
    soup = BeautifulSoup(page_text, 'html.parser')
    try:
        table_rows = soup.html.body
        table_rows = table_rows.find_all('div')[4]
        table_rows = table_rows.find_all('div')[5]
        table_rows = table_rows.find_all('div')[4]
        table_rows = table_rows.div.find_all('div')[1]
        table_rows = table_rows.div.table.tbody
        table_rows = table_rows.find_all('tr')[1:]
    except IndexError as e:
        raise ValueError("could not parse page: {}".format(e))

    result = {}
    for row in table_rows:
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


def parse_stats(stats_csv):
    skills = [
        'total', 'attack', 'defence', 'strength', 'hitpoints', 'ranged',
        'prayer', 'magic', 'cooking', 'woodcutting', 'fletching', 'fishing',
        'firemaking', 'crafting', 'smithing', 'mining', 'herblore', 'agility',
        'thieving', 'slayer', 'farming', 'runecraft', 'hunter', 'construction'
    ]
    result = {}

    fields = iter(stats_csv.split(','))
    result['username'] = next(fields)

    for skill in skills:
        rank = int(next(fields))
        rank = None if rank == -1 else rank
        level = int(next(fields))
        level = None if level == -1 else level
        xp = int(next(fields))
        xp = None if level == -1 else xp

        result[skill] = {
            'rank': rank,
            'level': level,
            'xp': xp
        }

    return result


def load_hiscores_data():
    print("loading hiscores data... ", end='')

    data_file = pathlib.Path(__file__).parent.parent.parent / 'data/processed/stats.pkl'
    with open(data_file.resolve(), 'rb') as f:
        dataset = pickle.load(f)
        
    # Unpack dataset keys: row names, col names and data values themselves.
    usernames = dataset['usernames']
    cols = dataset['features']
    data = dataset['stats']

    # Create three separate arrays, one each for rank, level and xp data.
    rank_data = data[:, 0::3]
    level_data = data[:, 1::3]
    xp_data = data[:, 2::3]
    skills = [col_name[:-len('_rank')] for col_name in cols[::3]]

    # Promote the arrays to dataframes.
    ranks = pd.DataFrame(data=rank_data, index=usernames, columns=skills)
    levels = pd.DataFrame(data=level_data, index=usernames, columns=skills)
    xp = pd.DataFrame(data=xp_data, index=usernames, columns=skills)

    print("done")

    return ranks, levels, xp


def exclude_missing(data):
    return data[data != -1]


def correlate_skills(skill_a, skill_b):
    levels_a = stats[:, features[skill_a + '_level']]
    levels_b = stats[:, features[skill_b + '_level']]
    keep_inds_a = levels_a > 0
    keep_inds_b = levels_b > 0
    keep_inds = np.logical_and(keep_inds_a, keep_inds_b)
    levels_a = levels_a[keep_inds]
    levels_b = levels_b[keep_inds]
    r_value, _ = pearsonr(levels_a, levels_b)
    return r_value
