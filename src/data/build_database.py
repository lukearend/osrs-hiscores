#!/usr/bin/env python3

""" Build a database of mappings from usernames to cluster ID. """

import os
import sys

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from tqdm import tqdm

from src.data import line_count, load_cluster_data, load_stats_data


def main(clusters_file, stats_file):
    print("building database...")
    try:
        url = os.environ["OSRS_MONGO_URI"]
    except KeyError as e:
        raise ValueError(f"{e} is not set in environment")

    print("connecting...", end=' ', flush=True)
    client = MongoClient(url, serverSelectionTimeoutMS=10000)
    db = client['osrs-hiscores']
    try:
        db.command('ping')
    except ServerSelectionTimeoutError:
        raise ValueError("could not connect to mongodb")
    collection = db['players']
    print("ok")

    num_players = line_count(stats_file) - 1
    if collection.count_documents({}) == num_players:
        print("database already populated, nothing to do")
        return

    usernames, skills, stats = load_stats_data(stats_file)
    _, splits, cluster_ids = load_cluster_data(clusters_file)

    print("writing records...")
    collection.drop()
    batch_size = 4096

    batch = []
    for i, username in enumerate(tqdm(usernames)):
        player_stats = [int(v) for v in stats[i, :]]
        player_clusters = {split: int(cluster_ids[i, j]) for j, split in enumerate(splits)}

        document = {
            '_id': username.lower(),
            'username': username,
            'cluster_ids': player_clusters,
            'stats': player_stats
        }
        batch.append(document)

        if len(batch) == batch_size:
            collection.insert_many(batch)
            batch = []

    if batch:
        collection.insert_many(batch)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
