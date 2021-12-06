#!/usr/bin/env python3

""" Convert stats CSV file to a pickled version for fast analysis. """

import csv
import pickle

import numpy as np
from tqdm import tqdm


IN_FILE = '../../data/processed/stats.csv'
OUT_FILE = '../../data/processed/stats.pkl'


def main():

    with open(IN_FILE, 'r') as f:

        print("reading stats CSV...")

        reader = csv.reader(f)
        fieldnames = next(reader)

        usernames = []
        stats = []
        for line in tqdm(reader):
            usernames.append(line[0])
            stats.append(np.array([int(i) for i in line[1:]]))

    stats = np.array(stats)

    with open(OUT_FILE, 'wb') as f:

        payload = {
            'usernames': usernames,
            'features': fieldnames[1:],
            'stats': stats
        }

        pickle.dump(payload, f)

    print("wrote to pkl file")


if __name__ == '__main__':
    main()
