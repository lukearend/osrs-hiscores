#!/usr/bin/env python3

""" Cleanup usernames scraped from OSRS hiscores. """

import csv
import sys
from collections import defaultdict

from tqdm import tqdm


def main(in_file, out_file):
    print("cleaning up usernames...")

    # Read rows from file and sort.
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        rows = []
        for line in tqdm(reader):
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

    print("writing results to CSV...")
    with open(out_file, 'w') as f:
        for rank, (name, total_level) in tqdm(enumerate(players, 1)):
            f.write('{},{},{}\n'.format(rank, name, total_level))

    print("done cleaning up usernames")


if __name__ == '__main__':
    in_file, out_file = sys.argv[1], sys.argv[2]
    main(in_file, out_file)