#!/usr/bin/env python3

""" Build a database of mappings from usernames to cluster ID. """

import pickle
import sys

from pymongo import MongoClient
from tqdm import tqdm


def main(stats_file, clusters_file):

    print("connecting to database")
    db = MongoClient('localhost', 27017)['osrs-hiscores']
    collection = db['players']

    print("reading usernames...")
    with open(stats_file, 'rb') as f:
        usernames = pickle.load(f)['usernames']

    print("reading cluster data...")
    with open(clusters_file, 'rb') as f:
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
    main(*sys.argv[1:3])
