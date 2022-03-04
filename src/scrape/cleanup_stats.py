#!/usr/bin/env python3

""" Cleanup stats data scraped from hiscores and write to CSV.
    This script runs in ~3 min on M1 Mac. """
import argparse
import csv

import numpy as np
from codetiming import Timer
from tqdm import tqdm

from src.common import osrs_statnames


@Timer(text="done cleaning stats dataset ({:.2f} sec)")
def main(in_file: str, out_file: str):
    """
    :param in_file: read raw scraped stats data from this CSV file
    :param out_file: output cleaned stats data to this CSV file
    """
    print("cleaning up stats dataset...")
    fields = ['username']
    for skill in osrs_statnames():
        fields.append(f'{skill}_rank')
        fields.append(f'{skill}_level')
        fields.append(f'{skill}_xp')

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape stats for the top 2 million OSRS players.""")
    parser.add_argument('infile', type=str, help="read raw scraped stats data from this CSV file")
    parser.add_argument('outfile', type=str, help="output cleaned stats data to this CSV file")
    args = parser.parse_args()
    main(args.infile, args.outfile)
