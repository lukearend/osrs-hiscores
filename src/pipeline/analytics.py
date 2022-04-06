""" Functions for analyzing clustering results. """

import numpy as np
from numpy.typing import NDArray


def get_cluster_sizes(cluster_ids: NDArray) -> NDArray:
    """ Compute the number of occurrences for each cluster ID in an array. """

    ids, counts = np.unique(cluster_ids.astype('int'), return_counts=True)
    sizes = np.zeros(max(ids) + 1)
    sizes[ids] = counts
    return sizes


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


def compute_stat_quartiles(player_vectors: NDArray) -> NDArray:
    """ Compute quartiles for each stat for a set of players. """

    # It is possible to have nan as a percentile value when all of the
    # players in a cluster happen to be unranked in a particular stat.
    return np.nanpercentile(player_vectors, axis=0, q=[0, 25, 50, 75, 100])
