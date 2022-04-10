""" Condense raw stats file from scraping into a clean skills dataset. """

import argparse
import shlex
import subprocess

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.analysis.data import dump_pkl
from src.analysis import osrs_skills
from src.scrape import csv_to_player, stat_ind


def main(in_file: str, out_file: str):
    print("reading raw scrape data...")
    stdout = subprocess.check_output(shlex.split(f"wc -l {in_file}"))  # count lines in file
    nlines = int(stdout.decode().strip().split()[0])  # stdout returns both line count and filename
    with open(in_file, 'r') as f:
        _ = f.readline()  # discard header
        players = []
        for line in tqdm(f.readlines(), total=nlines - 1):
            players.append(csv_to_player(line.strip()))

    # Deduplicate any records with matching usernames by taking the later one.
    print("cleaning...")
    seen = {}  # mapping from usernames to players seen so far
    for p in tqdm(players):
        if p.username not in seen.keys():
            seen[p.username] = p
        else:
            existing = seen[p.username]
            seen[p.username] = p if p.ts > existing.ts else existing
    players = seen.values()

    # Sort from best to worst and reassign ranks.
    print("sorting...")
    players = sorted(players, reverse=True)
    for i, player in enumerate(players, start=1):
        player.rank = i

    # Cast to a pandas DataFrame.
    print("converting to DataFrame...")
    skills = osrs_skills(include_total=True)
    skill_lvl_inds = np.array([stat_ind(f'{s}_level') for s in skills])

    unames = []
    stats = np.zeros((len(players), len(skills)), dtype='int')
    for i, p in tqdm(enumerate(players), total=len(players)):
        stats[i, :] = p.stats[skill_lvl_inds]
        unames.append(p.username)
    stats[stats == -1] = 0         # missing data
    stats = stats.astype('uint16')  # save size since all values in range 0-2277

    players_df = pd.DataFrame(data=stats, index=unames, columns=skills)

    dump_pkl(players_df, out_file)
    print(f"wrote results to {out_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Clean up and condense raw stats data.")
    parser.add_argument('-i', '--in-file', required=True, help="raw CSV file from scraping process")
    parser.add_argument('-o', '--out-file', required=True, help="output cleaned dataset to this file")
    args = parser.parse_args()
    main(args.in_file, args.out_file)
