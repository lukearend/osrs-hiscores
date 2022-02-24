#!/usr/bin/env python3

""" Compute size, quartiles and uniqueness for each cluster.
    This script runs in about ~5 mins on an M1 Mac.
"""

import pickle
import sys

import numpy as np

from src import load_clusterids_data, load_stats_data
from src.app import (compute_cluster_sizes, compute_cluster_quantiles,
                     compute_percent_uniqueness)


def compute_cluster_quartiles(stats, skills):
    splits =

    cluster_quartiles = defaultdict(dict)
    percentiles = [0, 25, 50, 75, 100]
    for s, split in enumerate(splits):
        print(f"computing quartiles for split '{split}'...")
        # Include total level when computing percentiles.
        dataset = None
        result = None
        num_clusters = max(cluster_ids[:, s])
        if split == 'all':
            dataset = stats
            result = np.zeros((num_clusters, len(percentiles), len(skills)))
        elif split == 'cb':
            dataset = stats[:, :8]  # Total level and the 7 combat skills
            result = np.zeros((num_clusters, len(percentiles), 8))
        elif split == 'noncb':
            total_levels = np.expand_dims(stats[:, 0], axis=1)
            dataset = np.concatenate([total_levels, stats[:, 8:]], axis=1)
            result = np.zeros((num_clusters, len(percentiles), len(skills) - 7))

        for i in tqdm(range(num_clusters)):
            cluster_inds = cluster_ids[:, s] == i
            cluster_points = dataset[cluster_inds]
            for j, p in enumerate(percentiles):
                # A good number of clusters have one or more nan columns. This is
                # because accounts in the cluster had one or more skills below the
                # threshold to have that skill's data included in the official OSRS
                # hiscores. We use np.nanpercentile and pass any nan columns on.
                result[i, j, :] = np.nanpercentile(cluster_points, axis=0, q=p)

        cluster_quartiles[split] = result
    pass  # todo: factor out


def compute_cluster_uniqueness():
    pass  # todo: factor out


def main(stats_file, clusters_file, out_file):
    _, splits, cluster_ids = load_clusterids_data(clusters_file)
    _, skills, stats = load_stats_data(stats_file)

    # Change missing stat values from -1 to Nan.
    stats = stats.astype('float')
    stats[stats < 0] = np.nan

    print("computing cluster sizes...")
    cluster_sizes = compute_cluster_sizes(cluster_ids, splits)

    # Compute 'percent uniqueness' for each cluster.
    print("computing cluster uniqueness...")
    num_players = len(stats)
    cluster_uniqueness = {}
    for split in splits:
        # An account's 'percent uniqueness' is the percentage of accounts
        # which are as unique or less unique than itself. First, line up
        # all clusters in order from smallest to largest (most to least
        # unique). Percent uniqueness for an account is then the number of
        # players in all clusters of the same size or larger than
        # that account's cluster, divided by the total number of players.
        # Accounts in a cluster of size 1 are 100% unique.
        sort_inds = np.argsort(cluster_sizes[split])
        sorted_sizes = cluster_sizes[split][sort_inds]
        sorted_uniqueness = np.cumsum(sorted_sizes[::-1])[::-1] / num_players
        unsort_inds = np.argsort(sort_inds)
        uniqueness = sorted_uniqueness[unsort_inds]
        cluster_uniqueness[split] = uniqueness

    cluster_data = {
        'sizes': cluster_sizes,
        'quartiles': cluster_quartiles,
        'uniqueness': cluster_uniqueness
    }
    with open(out_file, 'wb') as f:
        pickle.dump(cluster_data, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
