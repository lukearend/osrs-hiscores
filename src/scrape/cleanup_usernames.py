#!/usr/bin/env python3

""" Cleanup usernames scraped from OSRS hiscores. """
import argparse
import csv
from collections import defaultdict

from codetiming import Timer
from tqdm import tqdm


@Timer(text="done cleaning usernames ({:.2f} sec)")
def main(in_file, out_file):
    print("cleaning up usernames...")
    print("reading raw username data...")
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        rows = []
        for line in tqdm(reader):
            rows.append((int(line[0]), int(line[1]), line[2], int(line[3])))

    print("sorting...")
    rows = sorted(set(rows))

    # If a username shows up in more than one row, keep the row
    # where total level is highest (most recent) and discard the rest.
    total_levels = defaultdict(int)
    for row in tqdm(rows):
        name, total_level = row[2], row[3]
        if total_level > total_levels[name]:
            total_levels[name] = total_level

    # Sort players by total level and write to file.
    players = sorted(total_levels.items(), key=lambda item: item[1], reverse=True)

    print("writing results to csv...")
    with open(out_file, 'w') as f:
        for rank, (name, total_level) in tqdm(enumerate(players, 1)):
            f.write(f'{rank},{name},{total_level}\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape stats for the top 2 million OSRS players.""")
    parser.add_argument('infile', type=str, help="read raw scraped usernames from this CSV file")
    parser.add_argument('outfile', type=str, help="output cleaned username dataset to this CSV file")
    args = parser.parse_args()
    main(args.infile, args.outfile)
