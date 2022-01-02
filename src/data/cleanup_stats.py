#!/usr/bin/env python3

""" Cleanup stats data scraped from hiscores and write to CSV.
    This script runs in ~3 min on M1 Mac. """

import csv
import pathlib
import pickle
import sys

import numpy as np
from tqdm import tqdm


def main(in_file, out_file):
    print("cleaning up stats dataset...")

    skills_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/osrs_skills.csv'
    with open(skills_file, 'r') as f:
        skills = f.read().strip().split('\n')

    fields = ['username']
    for skill in skills:
        fields.append('{}_rank'.format(skill))
        fields.append('{}_level'.format(skill))
        fields.append('{}_xp'.format(skill))

    with open(in_file, 'r') as f:
        print("cleaning rank/level/xp data...")
        reader = csv.reader(f)

        username_list = []
        stats_list = []
        for line in tqdm(reader):
            if len(line) < len(fields):                # user not found during scraping
                continue

            username = line[0]
            stats = np.array([int(i) for i in line[1:len(fields)]])

            if stats[0] == -1:                          # missing total level
                continue

            # If a skill's level is 1 and rank/xp are missing, level is missing.
            for i in range(0, len(stats), 3):
                rank, level, xp = stats[i:i + 3]
                if (rank, level, xp) == (-1, 1, -1):
                    stats[i + 1] = -1

            username_list.append(username)
            stats_list.append(stats)

    usernames = np.array(username_list)
    stats = np.array(stats_list)

    # Sort descending by total level, breaking ties with xp and then original OSRS rank.
    print("sorting...")
    inds = np.lexsort((stats[:, 0], -stats[:, 2], -stats[:, 1]))
    stats = stats[inds]
    usernames = usernames[inds]

    # Rewrite ranks with this new sorting.
    stats[:, 0] = np.arange(1, stats.shape[0] + 1)

    with open(out_file, 'w') as f:
        print("writing results to csv...")
        writer = csv.DictWriter(f, fields)

        writer.writeheader()
        for username, user_stats in tqdm(zip(usernames, stats)):
            line = [username, *user_stats]
            line = dict(zip(fields, line))
            writer.writerow(line)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
