import argparse
import csv

import numpy as np
from numpy.random import default_rng
from tqdm import tqdm

from src.common import count_csv_rows


def main(in_file: str, out_file: str):
    print("building test dataset...")
    print("reading player stats...")

    nplayers = count_csv_rows(in_file)
    nstats = 3 * 24  # total and 23 skills each with rank, level, xp
    usernames = []
    stats = np.zeros((nplayers, nstats), dtype='int')
    with open(in_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for i in tqdm(range(nplayers)):
            line = next(reader)
            usernames.append(line[0])
            stats[i, :] = line[1:]

    print("subsampling...")
    nsamples = 1000
    rng = default_rng(0)
    randinds = rng.choice(nplayers, nsamples, replace=False)
    usernames = [usernames[i] for i in randinds]
    stats = stats[randinds, :]

    print("writing...")
    out_rows = np.zeros((nsamples, 1 + nstats), dtype='object')
    out_rows[:, 0] = usernames
    out_rows[:, 1:] = stats
    with open(out_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(out_rows)

    print("done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build a small dataset for testing.""")
    parser.add_argument('infile', type=str, help="load all player stats from this CSV file")
    parser.add_argument('outfile', type=str, help="write subsample of dataset to this CSV file")
    args = parser.parse_args()
    main(args.infile, args.outfile)
