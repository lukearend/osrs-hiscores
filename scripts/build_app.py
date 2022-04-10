#!/usr/bin/env python3

import argparse
from collections import OrderedDict
from typing import List

import pandas as pd
import xarray as xr
from pymongo.collection import Collection
from tqdm import tqdm

from src.analysis import load_splits
from src.analysis.app import SplitData, connect_mongo, PlayerResults, store_player_results, update_player_results, \
    mongo_insert_players, player_to_mongodoc, update_results_doc
from src.analysis.data import load_pkl, dump_pkl
from src.analysis.results import get_cluster_sizes, get_cluster_uniqueness


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
            cluster_sizes=list(cluster_sizes),
            cluster_uniqueness=list(get_cluster_uniqueness(cluster_sizes)),
            xyz_axlims={
                'x': (min(cluster_xyz['x']), max(cluster_xyz['x'])),
                'y': (min(cluster_xyz['y']), max(cluster_xyz['y'])),
                'z': (min(cluster_xyz['z']), max(cluster_xyz['z']))
            })
        app_data[split] = split_data

    return app_data


def do_in_batches(iterator, item_fn, batch_fn, total=None, batch_size=1000):
    with tqdm(total=total) as pbar:
        batch = []
        for i in iterator:
            result = item_fn(i)
            batch.append(result)
            if len(batch) >= batch_size:
                batch_fn(batch)
                pbar.update(len(batch))
                batch = []
        if batch:
            batch_fn(batch)
            pbar.update(len(batch))


def build_app_database(players: pd.DataFrame,
                       clusterids: pd.DataFrame,
                       collection: Collection, nclusters: int):

    def player_row_to_playerdoc(players_df_row):
        uname, player_stats = players_df_row
        player = PlayerResults(username=uname, stats=list(player_stats), clusterids=None)
        return player_to_mongodoc(player)

    def clusterids_row_to_updatedoc(clusterids_df_row):
        uname, player_clusterids = clusterids_df_row
        clustering_results = player_clusterids.to_dict()
        return update_results_doc(uname, k=nclusters, clusterids=clustering_results)

    if collection.count_documents({}) == 0:
        print("writing player stats to database...")
        do_in_batches(iterator=players.iterrows(),
                      item_fn=player_row_to_playerdoc,
                      batch_fn=collection.insert_many,
                      total=len(players))

    print(f"writing player cluster IDs to database (k={nclusters})...")
    do_in_batches(iterator=clusterids.iterrows(),
                  item_fn=clusterids_row_to_updatedoc,
                  batch_fn=collection.update_many


    with tqdm(total=len(players)) as pbar:
        batch = []
        for uname, player_clusterids in tqdm(clusterids.iterrows(), total=len(clusterids)):
            batch.append(update)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Build data file and database for application to use.""")
    parser.add_argument('--stats-file', type=str, help="load player stats from this file")
    parser.add_argument('--clusterids-file', type=str, help="load player cluster IDs from this file")
    parser.add_argument('--centroids-file', type=str, help="load cluster centroids from this file")
    parser.add_argument('--quartiles-file', type=str, help="load cluster quartiles from this file")
    parser.add_argument('--xyz-file', type=str, help="load cluster 3D coordinates from this file")
    parser.add_argument('--out-file', type=str, help="write application data object to this file")
    parser.add_argument('-u', '--mongo-url', type=str, help="use Mongo instance running at this URL")
    parser.add_argument('-c', '--collection', type=str, help="name of collection to populate")
    parser.add_argument('-k', '--n-clusters', type=int, help="number of clusters in results set to export")
    args = parser.parse_args()

    print("loading data...")
    players_df = load_pkl(args.stats_file)
    clusterids_df = load_pkl(args.clusterids_file)
    centroids_dict = load_pkl(args.centroids_file)
    quartiles_dict = load_pkl(args.quartiles_file)
    xyz_dict = load_pkl(args.xyz_file)

    appdata = build_app_data(load_splits(), clusterids_df, centroids_dict, quartiles_dict, xyz_dict)
    dump_pkl(appdata, args.out_file)
    print(f"wrote app data to {args.out_file}")

    coll = connect_mongo(args.mongo_url, args.collection)
    build_app_database(players_df, clusterids_df, coll, args.nclusters)
