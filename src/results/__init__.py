import pickle
from dataclasses import dataclass
from typing import List, Dict, Any

import numpy as np
from numpy.typing import NDArray

from src.common import DatasetSplit


@dataclass
class ClusterData:
    """ Contains app data for a set of clusters. """
    xyz: Dict  # TODO: becomes NDArray once umap params frozen
    sizes: NDArray
    centroids: NDArray
    quartiles: NDArray
    uniqueness: NDArray


@dataclass
class SplitData:
    """ Contains app data for one split of the dataset. """
    skills: List[str]
    clusterdata: ClusterData
    axlims: Dict  # TODO: becomes Dict[NDArray] once umap params frozen


@dataclass
class AppData:
    """ Contains all data needed to run Dash app. """
    splitnames: List[DatasetSplit]
    splitdata: Dict[str, SplitData]


@dataclass
class ClusterAnalytics:
    """ Contains analytics for a set of clusters. """
    sizes: NDArray
    quartiles: NDArray
    uniqueness: NDArray


def load_clusters_xyz(file: str) -> Dict[str, Dict]:  # TODO: becomes NDArray once umap params frozen
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_cluster_analytics(file: str) -> Dict[str, ClusterAnalytics]:
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_app_data(file: str) -> AppData:
    with open(file, 'rb') as f:
        return pickle.load(f)


def compute_cluster_sizes(clusterids: NDArray) -> NDArray:
    """
    Compute the number of occurrences for each cluster ID in an array.

    :param cluster_ids: array of cluster IDs
    :return: array where value at index N is the size of cluster N
    """
    ids, counts = np.unique(clusterids.astype('int'), return_counts=True)
    sizes = np.zeros(max(ids) + 1)
    sizes[ids] = counts
    return sizes


def compute_cluster_uniqueness(cluster_sizes: NDArray) -> NDArray:
    """
    Compute uniqueness for a set of clusters given their sizes.

    A cluster's 'percent uniqueness' is its value in the CMF created
    by summing all cluster sizes from smallest to largest. In other
    words, if all clusters are lined up in order from smallest to largest
    (containing most unique to least unique players), percent uniqueness
    is the number of players in all clusters of the same size or larger
    than that account's cluster, divided by the total number of players.

    :param cluster_sizes: array of cluster sizes
    :return: array of percent uniqueness scores for the corresponding clusters
    """
    nplayers = np.sum(cluster_sizes)
    sort_inds = np.argsort(cluster_sizes)
    sorted_sizes = cluster_sizes[sort_inds]
    sorted_uniqueness = np.cumsum(sorted_sizes[::-1])[::-1] / nplayers  # sum from right-hand side
    unsort_inds = np.argsort(sort_inds)
    cluster_uniqueness = sorted_uniqueness[unsort_inds]
    return cluster_uniqueness


def compute_stat_quartiles(player_vectors: NDArray) -> NDArray:
    """
    Compute quartiles (min, 25th percentile, median, 75 percentile, max)
    in each skill for the given set of player vectors. It is possible to
    have nan as a percentile value when all of the players in a cluster
    happen to be unranked in a particular stat.

    :param player_vectors: 2D array of player stat vectors
    :return: 2D array with five rows, giving percentile value in each
             skill for the 0, 25, 50, 75, and 100th percentiles
    """
    return np.nanpercentile(player_vectors, axis=0, q=[0, 25, 50, 75, 100])


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """
    username: str
    clusterids: Dict[str, int]  # resulting cluster ID for each split of the dataset
    stats: List[int]


def player_results_to_mongodoc(player: PlayerResults) -> Dict[str, Any]:
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'clusterids': player.clusterids,
        'stats': player.stats
    }


def mongodoc_to_player_results(doc: Dict[str, Any]) -> PlayerResults:
    return PlayerResults(
        username=doc['username'],
        clusterids=doc['clusterids'],
        stats=doc['stats']
    )
