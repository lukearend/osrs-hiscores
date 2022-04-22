#!/usr/bin/env python3

import argparse
import sys
from collections import OrderedDict
from typing import List

import pandas as pd
import xarray as xr
from pymongo.collection import Collection
from tqdm import tqdm

from src.analysis import load_splits
from src.analysis.app import SplitData, PlayerResults, connect_mongo, player_to_mongodoc
from src.analysis.data import load_pkl, dump_pkl
from src.analysis.results import get_cluster_sizes, get_cluster_uniqueness


class PartialCollection(Exception):
    """ Raised upon finding a partially exported collection. """


def build_app_data(splits: OrderedDict[str, List[str]],
                   clusterids: pd.DataFrame,
                   centroids: OrderedDict[str, pd.DataFrame],
                   quartiles: OrderedDict[str, xr.DataArray],
                   xyz: OrderedDict[str, pd.DataFrame]) -> OrderedDict[str, SplitData]:

    app_data = OrderedDict()
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

    batch_size = 1000
    last_uname = players.index[-1]

    if not collection.find_one({'_id': last_uname.lower()}):
        if collection.count_documents({}) > 0:
            raise PartialCollection

        print(f"exporting player stats to database...")
        with tqdm(total=len(players)) as pbar:
            batch = []
            for uname, player_stats in players.iterrows():
                player_clusterids=clusterids.loc[uname].to_dict()
                player = PlayerResults(username=uname, stats=list(player_stats), clusterids=player_clusterids)
                batch.append(player_to_mongodoc(player))
                if len(batch) >= batch_size:
                    collection.insert_many(batch)
                    pbar.update(len(batch))
                    batch = []
            if batch:
                collection.insert_many(batch)
                pbar.update(len(batch))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Build data file and database for application to use.""")
    parser.add_argument('--stats-file', type=str, help="load player stats from this file")
    parser.add_argument('--clusterids-file', type=str, help="load player cluster IDs from this file")
    parser.add_argument('--centroids-file', type=str, help="load cluster centroids from this file")
    parser.add_argument('--quartiles-file', type=str, help="load cluster quartiles from this file")
    parser.add_argument('--xyz-file', type=str, help="load cluster 3D coordinates from this file")
    parser.add_argument('--out-file', type=str, help="write application data object to this file")
    parser.add_argument('--mongo-url', type=str, help="use Mongo instance running at this URL")
    parser.add_argument('--collection', type=str, help="export player stats to this collection")
    args = parser.parse_args()

    print("building app data...")
    players_df = load_pkl(args.stats_file)
    clusterids_df = load_pkl(args.clusterids_file)
    centroids_dict = load_pkl(args.centroids_file)
    quartiles_dict = load_pkl(args.quartiles_file)
    xyz_dict = load_pkl(args.xyz_file)

    coll = connect_mongo(args.mongo_url, args.collection)
    appdata = build_app_data(load_splits(), clusterids_df, centroids_dict, quartiles_dict, xyz_dict)
    try:
        build_app_database(players_df, clusterids_df, coll)
    except PartialCollection as e:
        print(f"found partial collection, exiting")
        sys.exit(1)
    dump_pkl(appdata, args.out_file)
    print(f"wrote app data to {args.out_file}")
