#!/usr/bin/env python3

""" Build a database of mappings from usernames to cluster ID. """

import pickle
import sys

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from tqdm import tqdm


def main(stats_file, clusters_file, mongo_port):

    print("building database...")

    print("connecting...", end=' ', flush=True)
    url = 'localhost:{}'.format(mongo_port)
    client = MongoClient(url, serverSelectionTimeoutMS=10000)
    db = client['osrs-hiscores']
    try:
        db.command('ping')
    except ServerSelectionTimeoutError:
        raise ValueError("could not connect to mongodb")
    collection = db['players']
    print("ok")

    print("loading username list...")
    with open(stats_file, 'rb') as f:
        usernames = pickle.load(f)['usernames']

    with open(clusters_file, 'rb') as f:
        clusters = pickle.load(f)
    splits = clusters.keys()

    # If the final username in usernames file has an entry in database,
    # assume database has already been filled and take no further action.
    if collection.find_one(usernames[-1].lower()):
        print("database already populated, nothing to do")
        print()
        return

    print("writing records...")
    collection.drop()
    batch_size = 4096

    batch = []
    for i, username in enumerate(tqdm(usernames)):

        document = {
            '_id': username.lower(),
            'username': username,
            'cluster_id': {split: int(clusters[split]['cluster_ids'][i]) for split in splits}
        }
        batch.append(document)

        if len(batch) == batch_size:
            collection.insert_many(batch)
            batch = []

    if batch:
        collection.insert_many(batch)

    print("done")
    print()


if __name__ == '__main__':
    main(*sys.argv[1:3], int(sys.argv[3]))
