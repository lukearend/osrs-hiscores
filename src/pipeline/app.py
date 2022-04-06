""" Code for building app dependencies. """

from dataclasses import dataclass
from typing import List, OrderedDict

import pandas as pd
from numpy.typing import NDArray
from pymongo.collection import Collection
from tqdm import tqdm

from src.analytics.results import get_cluster_sizes, get_cluster_uniqueness
from src.common import Player


@dataclass
class SplitData:
    """ Contains app data for one split of the dataset. """

    skills: List[str]
    cluster_centroids: NDArray
    cluster_sizes: NDArray
    cluster_quartiles: NDArray
    cluster_uniqueness: NDArray
    cluster_xyz: NDArray
    xyz_axlims: NDArray


def build_appdata_obj(centroids_df, xyz_df, quartiles_df, clusterids_df) -> OrderedDict[str, SplitData]:
    cluster_sizes = {}
    for s, split in enumerate(splits):
        cluster_sizes[split] = get_cluster_sizes(clusterids[:, s])

    cluster_uniqueness = {}
    for split in splits:
        cluster_uniqueness[split] = get_cluster_uniqueness(cluster_sizes[split])

    splits = load_splits()
    for split, skills in splits:

        axlims = {}
        for n_neighbors, nn_dict in cluster_xyz[split].items():
            axlims[n_neighbors] = {}
            for min_dist in nn_dict.keys():
                xyz = cluster_xyz[split.name][n_neighbors][min_dist]
                axlims[n_neighbors][min_dist] = compute_minmax(xyz)

        split_results = SplitData(
            skills=skills
            cluster_xyz=cluster_xyz[split.name],
            cluster_sizes=cluster_analytics[split.name].sizes,
            cluster_centroids=centroids[split.name],
            cluster_quartiles=cluster_analytics[split.name].quartiles,
            cluster_uniqueness=cluster_analytics[split.name].uniqueness
            clusterdata=cluster_data,
            xyz_axlims=axlims
        )
        results[split.name] = split_results


def populate_collection(players_df: pd.DataFrame, clusterids_df: pd.DataFrame, collection: Collection):

    # todo: decide - one collection for all, or two? let's go with two for now.

    nplayers = len(players_df)
    ndocs = collection.count_documents({})
    if not drop:
        if ndocs == nplayers:
            print("database already populated, nothing to do")
            sys.exit(0)
        if ndocs > 0:
            yesno = input("database partially populated. overwrite? [y/n] ")
            if yesno.lower() != 'y':
                print("database not modified, exiting")
                sys.exit(0)

    _, splits, clusterids = load_clusterids_data(clusters_file)
    usernames, skills, stats = load_stats_data(stats_file, include_total=True)

    if ndocs > 0:
        collection.drop()
        print("dropped existing collection")

    print("writing records...")
    batch_size = 4096
    batch = []
    for i, username in enumerate(tqdm(usernames)):
        player_stats = [int(v) for v in stats[i, :]]
        ids_per_split = {split: int(clusterids[i, j]) for j, split in enumerate(splits)}
        player = Player(
            username=username,
            clusterid=ids_per_split,
            stats=player_stats
        )
        doc = playerdata_to_mongodoc(player)
        batch.append(doc)
        if len(batch) == batch_size:
            collection.insert_many(batch)
            batch = []
    if batch:
        collection.insert_many(batch)
    pass
