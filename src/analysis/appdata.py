""" Analytics on clustering results. """

from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from numpy.typing import NDArray
from pymongo.collection import Collection


@dataclass
class SplitResults:
    """ Clustering results for one split of the dataset. """

    skills: List[str]                # length nskills in split
    cluster_quartiles: xr.DataArray  # shape (5, nclusters, nskills + 1), includes total level
    cluster_centroids: pd.DataFrame  # shape (nclusters, nskills)
    cluster_xyz: pd.DataFrame        # shape (nclusters, 3)
    cluster_sizes: NDArray           # length nclusters
    cluster_uniqueness: NDArray      # length nclusters
    xyz_axlims: Dict[str, Tuple[float, float]]


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """

    username: str
    stats: List[int]            # includes total level
    clusterids: Dict[str, int]  # cluster ID for each split of the dataset


def player_to_mongodoc(player: PlayerResults):
    doc = {
        '_id': player.username.lower(),
        'username': player.username,
        'stats': player.stats
    }
    if player.clusterids:
        doc['clusterids'] = {str(k): ids_dict for k, ids_dict in player.clusterids.items()}
    else:
        doc['clusterids'] = {}
    return doc


def mongo_get_player(coll: Collection, username: str) -> PlayerResults:
    doc = coll.find_one({'_id': username.lower()})
    if not doc:
        return None
    return PlayerResults(
        username=doc['username'],
        clusterids=doc['clusterids'],
        stats=doc['stats']
    )


def get_cluster_sizes(cluster_ids: NDArray) -> NDArray:
    """ Compute the number of occurrences for each cluster ID in an array. """

    ids, counts = np.unique(cluster_ids, return_counts=True)
    sizes = np.zeros(max(ids) + 1)
    sizes[ids] = counts
    return sizes.astype('int')


def get_cluster_uniqueness(cluster_sizes: NDArray) -> NDArray:
    """ Compute cluster uniqueness. A cluster's 'uniqueness' is its value in
    the cumulative mass function created by summing all cluster sizes from
    smallest to largest. In other words, if all clusters are lined up in order
    from smallest to largest (containing most unique to least unique players),
    a cluster's uniqueness is the number of players in all clusters of the same
    size or larger than that cluster, divided by the total number of players. """

    nplayers = np.sum(cluster_sizes)
    sort_inds = np.argsort(cluster_sizes)
    sorted_sizes = cluster_sizes[sort_inds]
    sorted_uniqueness = np.cumsum(sorted_sizes[::-1])[::-1] / nplayers  # cumsum from right side
    unsort_inds = np.argsort(sort_inds)
    cluster_uniqueness = sorted_uniqueness[unsort_inds]
    return cluster_uniqueness
