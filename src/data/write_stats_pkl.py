#!/usr/bin/env python3

""" Convert stats CSV file to a pickled version for fast analysis. """

import csv
import pickle
import sys

import numpy as np
from tqdm import tqdm


def main(in_file, out_file):

    print("converting stats csv to pickle file...")
    with open(in_file, 'r') as f:

        reader = csv.reader(f)
        fieldnames = next(reader)

        usernames = []
        stats = []
        for line in tqdm(reader):
            usernames.append(line[0])
            stats.append(np.array([int(i) for i in line[1:]]))

    stats = np.array(stats)

    with open(out_file, 'wb') as f:

        payload = {
            'usernames': usernames,
            'features': fieldnames[1:],
            'stats': stats
        }

        pickle.dump(payload, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
