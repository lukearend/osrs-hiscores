#!/usr/bin/env python3

""" Write a lookup dictionary from usernames to cluster ID. """

import pickle


STATS_FILE = '../../data/processed/stats.pkl'
CLUSTERS_FILE = '../../data/processed/clusters.pkl'
OUT_FILE = '../../data/processed/players.pkl'


def main():
    print("writing mapping from player names to cluster ID...")

    print("reading stats data...")
    with open(STATS_FILE, 'rb') as f:
        usernames = pickle.load(f)['usernames']

    print("reading cluster data...")
    with open(CLUSTERS_FILE, 'rb') as f:
        clusters = pickle.load(f)

    out = {}
    for split, cluster_data in clusters.items():

        mapping = {}
        for username, cluster_id in zip(usernames, cluster_data['cluster_ids']):
            key = username.lower()
            mapping[key] = {
                'name': username,
                'cluster_id': cluster_id

            }

        out[split] = mapping

    print("writing player clusters file...")
    with open(OUT_FILE, 'wb') as f:
        pickle.dump(out, f)

    print("done")


if __name__ == '__main__':
    main()
