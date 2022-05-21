#!/usr/bin/env python3

""" Build player stat/clusters database for main application. """

import argparse

import pandas as pd
from pymongo.collection import Collection
from tqdm import tqdm

from src.data.db import connect_mongo, player_to_mongodoc
from src.data.io import load_pkl
from src.data.types import PlayerResults


def main(players: pd.DataFrame,
         clusterids: pd.DataFrame,
         collection: Collection,
         batch_size: int = 5000):

    if collection.count_documents({}) > 0:
        print("found partial collection, dropping")
        coll.drop()

    with tqdm(total=len(players)) as pbar:
        def export_batch(docs):
            collection.insert_many(docs)
            pbar.update(len(docs))

        batch = []
        for uname, player_stats in players.iterrows():
            player_clusterids = clusterids.loc[uname].to_dict()
            player = PlayerResults(username=uname, stats=list(player_stats), clusterids=player_clusterids)
            batch.append(player_to_mongodoc(player))

            if len(batch) >= batch_size:
                export_batch(batch)
                batch = []

        if batch:
            export_batch(batch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build data file and database for application to use.")
    parser.add_argument('--stats-file', required=True, help="load player stats from this file")
    parser.add_argument('--clusterids-file', required=True, help="load player cluster IDs from this file")
    parser.add_argument('--mongo-url', required=True, help="use Mongo instance running at this URL")
    parser.add_argument('--collection', required=True, help="export player stats to this collection")
    args = parser.parse_args()

    print("exporting player stats to database...")

    players_df = load_pkl(args.stats_file)
    clusterids_df = load_pkl(args.clusterids_file)
    coll = connect_mongo(args.mongo_url, args.collection)

    last_uname = players_df.index[-1]
    if coll.find_one({'_id': last_uname.lower()}):
        print("database collection is already populated")

    main(players_df, clusterids_df, coll)
