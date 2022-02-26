from dataclasses import dataclass
from typing import List, Dict

import numpy as np
from numpy.typing import NDArray

from src.common import DataSplit


@dataclass
class ClusterData:
    xyz: NDArray
    sizes: NDArray
    centroids: NDArray
    quartiles: NDArray
    uniqueness: NDArray


@dataclass
class SplitResults:
    skills: List[str]
    clusters: ClusterData
    axlims: Dict


@dataclass
class AppData:
    splitnames: List[DataSplit]
    results: Dict[str, SplitResults]


def compute_cluster_sizes(clusterids: NDArray) -> NDArray:
    """
    Compute the number of occurrences for each cluster ID in an array.
    :param cluster_ids: array of cluster IDs
    :return: array where value at index N is the size of cluster N
    """
    ids, counts = np.unique(clusterids.astype('int'), return_index=True)
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


def compute_skill_quartiles(player_vectors: NDArray) -> NDArray:
    """
    Compute quartiles (min, 25th percentile, median, 75 percentile, max)
    in each skill for the given set of player vectors.
    :param stats: 2D array of player skill vectors
    :return: 2D array with five rows, giving percentile value in each
             skill for the 0, 25, 50, 75, and 100th percentiles
    """
    quartiles = np.zeros((5, player_vectors.shape[1]))
    for i, p in enumerate([0, 25, 50, 75, 100]):
        # Use np.nanpercentile as player vectors may have missing data.
        quartiles[i, :] = np.nanpercentile(player_vectors, axis=0, q=p)
