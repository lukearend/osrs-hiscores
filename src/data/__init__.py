import csv
from subprocess import check_output

import numpy as np
from tqdm import tqdm


def line_count(file):
    return int(check_output(['wc', '-l', file]).split()[0])


def load_stats_data(file):
    print("reading stats data...")

    num_players = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)               # Discard header

        skills = []
        for field in header[2::3]:
            skills.append(field[:-len('_level')])

        usernames = np.zeros(num_players, dtype='<U12')
        stats = np.zeros((num_players, len(skills)), dtype='int')
        with tqdm(total=num_players) as pbar:
            for line in tqdm(reader):
                usernames[i] = line[0]
                stats[i, :] = line[2::3]    # Just take skill level (not rank, xp)
                pbar.update(1)

    return usernames, skills, stats


def load_cluster_data(file):
    print("loading cluster data...")

    num_players = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        splits = header[1:]

        usernames = np.zeros(num_players, dtype='<U12')
        cluster_ids = np.zeros((num_players, len(splits)), dtype='int')
        with tqdm(total=num_players) as pbar:
            for i, line in enumerate(reader):
                usernames[i] = line[0]
                cluster_ids[i, :] = line[1:]
                pbar.update(1)

    return usernames, splits, cluster_ids
