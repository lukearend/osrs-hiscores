#!/usr/bin/env python3

""" Build application data and database. """

import argparse
import collections
from typing import List, OrderedDict

import pandas as pd
import xarray as xr
from pymongo.collection import Collection
from tqdm import tqdm

from src.analysis.app import SplitData, PlayerResults, connect_mongo, player_to_mongodoc
from src.analysis.data import load_pkl, dump_pkl, load_json
from src.analysis.results import get_cluster_sizes, get_cluster_uniqueness


def build_app_data(splits: OrderedDict[str, List[str]],
                   clusterids: pd.DataFrame,
                   centroids: OrderedDict[str, pd.DataFrame],
                   quartiles: OrderedDict[str, xr.DataArray],
                   xyz: OrderedDict[str, pd.DataFrame]) -> OrderedDict[str, SplitData]:

    app_data = collections.OrderedDict()
    for split, skills_in_split in splits.items():
        cluster_xyz = xyz[split]
        cluster_sizes = get_cluster_sizes(clusterids[split])
        split_data = SplitData(
            skills=skills_in_split,
            cluster_quartiles=quartiles[split],
            cluster_centroids=centroids[split],
            cluster_xyz=cluster_xyz,
            cluster_sizes=cluster_sizes.astype('int'),
            cluster_uniqueness=get_cluster_uniqueness(cluster_sizes),
            xyz_axlims={
                'x': (min(cluster_xyz['x']), max(cluster_xyz['x'])),
                'y': (min(cluster_xyz['y']), max(cluster_xyz['y'])),
                'z': (min(cluster_xyz['z']), max(cluster_xyz['z']))
            })
        app_data[split] = split_data

    return app_data


def build_app_database(players: pd.DataFrame,
                       clusterids: pd.DataFrame,
                       collection: Collection):

    if collection.count_documents({}) > 0:
        print("found partial collection, dropping")
        coll.drop()

    print(f"exporting player stats to database...")
    with tqdm(total=len(players)) as pbar:
        batch = []
        for uname, player_stats in players.iterrows():
            player_clusterids=clusterids.loc[uname].to_dict()
            player = PlayerResults(username=uname, stats=list(player_stats), clusterids=player_clusterids)
            batch.append(player_to_mongodoc(player))
            if len(batch) >= 5000:
                collection.insert_many(batch)
                pbar.update(len(batch))
                batch = []
        if batch:
            collection.insert_many(batch)
            pbar.update(len(batch))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build data file and database for application to use.")
    parser.add_argument('--stats-file', help="load player stats from this file")
    parser.add_argument('--splits-file', help="load skills in each split from this file")
    parser.add_argument('--clusterids-file', help="load player cluster IDs from this file")
    parser.add_argument('--centroids-file', help="load cluster centroids from this file")
    parser.add_argument('--quartiles-file', help="load cluster quartiles from this file")
    parser.add_argument('--xyz-file', help="load cluster 3D coordinates from this file")
    parser.add_argument('--out-file', help="write application data object to this file")
    parser.add_argument('--mongo-url', help="use Mongo instance running at this URL")
    parser.add_argument('--collection', help="export player stats to this collection")
    args = parser.parse_args()

    print("building app data...")
    splits = load_json(args.splits_file)
    players_df = load_pkl(args.stats_file)
    clusterids_df = load_pkl(args.clusterids_file)
    centroids_dict = load_pkl(args.centroids_file)
    quartiles_dict = load_pkl(args.quartiles_file)
    xyz_dict = load_pkl(args.xyz_file)

    appdata = build_app_data(splits, clusterids_df, centroids_dict, quartiles_dict, xyz_dict)
    dump_pkl(appdata, args.out_file)
    print(f"wrote app data to {args.out_file}")

    coll = connect_mongo(args.mongo_url, args.collection)
    last_uname = players_df.index[-1]
    if not coll.find_one({'_id': last_uname.lower()}):
        build_app_database(players_df, clusterids_df, coll)
    else:
        print("database collection is already populated")
