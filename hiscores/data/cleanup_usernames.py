#!/usr/bin/env python3

import csv
from collections import defaultdict


IN_FILE = '../../data/raw/usernames-raw.csv'
OUT_FILE = '../../data/interim/usernames.csv'


def main():
    print("cleaning up usernames...")

    # Read rows from file and sort.
    with open(IN_FILE, 'r') as f:
        reader = csv.reader(f)
        rows = []
        for line in reader:
            rows.append((int(line[0]), int(line[1]), line[2], int(line[3])))

    rows = sorted(set(rows))

    # If a username shows up in more than one row, keep the row
    # where total level is highest (most recent) and discard the rest.
    players = defaultdict(int)
    for row in rows:
        name, total_level = row[2], row[3]
        if total_level > players[name]:
            players[name] = total_level

    # Sort players by total level and write to file.
    players = sorted(players.items(), key=lambda item: item[1], reverse=True)

    with open(OUT_FILE, 'w') as f:
        for rank, (name, total_level) in enumerate(players, 1):
            f.write('{},{},{}\n'.format(rank, name, total_level))

    print("done cleaning up usernames")


if __name__ == '__main__':
    main()
