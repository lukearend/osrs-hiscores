#!/usr/bin/env python3

import csv
import pickle

import numpy as np


IN_FILE = '../../data/raw/stats-raw.csv'
OUT_CSV_FILE = '../../data/interim/stats-tmp.csv'
OUT_PKL_FILE = '../../data/interim/stats-tmp.pkl'


def main():
    with open('../../reference/skills.csv', 'r') as f:
        skills = f.read().strip().split('\n')

    fieldnames = ['username']
    for skill in skills:
        fieldnames.append('{}_rank'.format(skill))
        fieldnames.append('{}_level'.format(skill))
        fieldnames.append('{}_xp'.format(skill))

    with open(IN_FILE, 'r') as f:
        print("reading raw data...")
        reader = csv.reader(f)

        usernames = []
        stats = []
        for line in reader:
            if len(line) < 73:
                continue

            usernames.append(line[0])
            stats.append(np.array([int(i) for i in line[1:73]]))

        usernames = np.array(usernames)
        stats = np.array(stats)

    print("cleaning data...")

    # For all level columns (but not column 1, total level)
    # change any 1s to -1s. These are missing values.
    for col_i in range(4, 71, 3):
        column = stats[:, col_i]
        column[column == 1] = -1

    # Sort descending by total level, breaking ties by total xp.
    inds = np.lexsort((-stats[:, 2], -stats[:, 1]))
    stats = stats[inds]
    usernames = usernames[inds]

    with open(OUT_CSV_FILE, 'w') as f:
        print("writing results to CSV...")
        writer = csv.DictWriter(f, fieldnames)

        writer.writeheader()
        for username, stats in zip(usernames, stats):
            line = [username, *stats]
            line = dict(zip(fieldnames, line))
            writer.writerow(line)

    with open(OUT_PKL_FILE, 'w') as f:
        print("pickling results...")

        payload = {
            'usernames': list(usernames),
            'features': fieldnames[1:]
            'stats': stats
        }

        pickle.dump(payload, f)

    print("done")


if __name__ == '__main__':
    main()
