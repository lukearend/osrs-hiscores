#!/usr/bin/env python3

""" Unpickle clustering results file and write to CSV. """

import csv
import pickle

from tqdm import tqdm


STATS_FILE = '../../data/processed/stats.pkl'
CLUSTERS_FILE = '../../data/raw/clusters-raw.pkl'
OUT_FILE = '../../data/processed/clusters.csv'


def main():
    print("getting usernames...")
    with open(STATS_FILE, 'rb') as f:
        contents = pickle.load(f)
        usernames = contents['usernames']

    with open(CLUSTERS_FILE, 'rb') as f:
        clusters = pickle.load(f)

    print("writing clustering results to CSV...")
    with open(OUT_FILE, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['username', 'all', 'cb', 'noncb'])

        for i, username in tqdm(enumerate(usernames)):
            all_id = clusters['all'][i]
            cb_id = clusters['cb'][i]
            noncb_id = clusters['noncb'][i]

            writer.writerow([username, all_id, cb_id, noncb_id])


if __name__ == '__main__':
    main()
