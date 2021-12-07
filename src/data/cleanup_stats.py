#!/usr/bin/env python3

""" Cleanup stats data scraped from hiscores and write to CSV. """

import csv
import pathlib
import pickle
import sys

import numpy as np
from tqdm import tqdm


def main(in_file, out_file):
    print("cleaning up stats dataset...")

    skills_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/skills.csv'
    with open(skills_file, 'r') as f:
        skills = f.read().strip().split('\n')

    fieldnames = ['username']
    for skill in skills:
        fieldnames.append('{}_rank'.format(skill))
        fieldnames.append('{}_level'.format(skill))
        fieldnames.append('{}_xp'.format(skill))

    with open(in_file, 'r') as f:
        print("reading in rank/level/xp data...")
        reader = csv.reader(f)

        usernames = []
        stats = []
        for line in tqdm(reader):
            if len(line) < 73:
                continue

            usernames.append(line[0])
            stats.append(np.array([int(i) for i in line[1:73]]))

    usernames = np.array(usernames)
    stats = np.array(stats)

    print("sorting...")

    # Sort descending by total level, breaking ties by total xp.
    inds = np.lexsort((-stats[:, 2], -stats[:, 1]))
    stats = stats[inds]
    usernames = usernames[inds]

    # Rewrite ranks with this new sorting.
    stats[:, 0] = np.arange(1, stats.shape[0] + 1)

    with open(out_file, 'w') as f:
        print("writing results to csv...")
        writer = csv.DictWriter(f, fieldnames)

        writer.writeheader()
        for username, user_stats in tqdm(zip(usernames, stats)):
            line = [username, *user_stats]
            line = dict(zip(fieldnames, line))
            writer.writerow(line)

    print("done")
    print()


if __name__ == '__main__':
    main(*sys.argv[1:])
