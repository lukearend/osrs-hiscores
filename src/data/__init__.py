import csv

import numpy as np
from tqdm import tqdm


def load_stats_data(file):
    print("reading stats data...")
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)            # Discard header

        skills = []
        for field in header[2::3]:
            skills.append(field[:-len('_level')])

        usernames = []
        stats_list = []
        for line in tqdm(reader):
            username = line[0]
            player_levels = [int(n) for n in line[2::3]]
            usernames.append(username)
            stats_list.append(player_levels)

    print("building data array...")
    usernames = np.array(usernames)
    stats = np.array(stats_list, dtype='int')
    del stats_list

    return usernames, skills, stats
