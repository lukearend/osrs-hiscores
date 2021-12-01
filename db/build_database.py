#!/usr/bin/env python3

""" Build a database of mappings from usernames to cluster ID. """

import pickle

from pymongo import MongoClient
from tqdm import tqdm


STATS_FILE = '../data/processed/stats.pkl'
CLUSTERS_FILE = '../data/processed/clusters.pkl'


def main():
    print("connecting to database")

    client = MongoClient('localhost:27017')
    db = client['osrs-hiscores']
    collection = db['players']

    print("reading usernames...")
    with open(STATS_FILE, 'rb') as f:
        usernames = pickle.load(f)['usernames']

    print("reading cluster data...")
    with open(CLUSTERS_FILE, 'rb') as f:
        clusters = pickle.load(f)

    print("writing player cluster IDs to database...")
    splits = clusters.keys()
    for i, username in enumerate(tqdm(usernames)):
        document = {
            'username': username,
            'cluster_id': {split: int(clusters[split]['cluster_ids'][i]) for split in splits}
        }
        collection.update_one(
            {'_id': username.lower()},
            {'$set': document},
            upsert=True)

    print("done")


if __name__ == '__main__':
    main()
