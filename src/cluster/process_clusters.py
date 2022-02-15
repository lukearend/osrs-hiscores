#!/usr/bin/env python3

""" Compute size, quartiles and uniqueness for each cluster.
    This script runs in about ~5 mins on an M1 Mac.
"""

import pickle
import sys
from collections import defaultdict

import numpy as np
from tqdm import tqdm

from src import load_cluster_data, load_stats_data


def main(stats_file, clusters_file, out_file):
    print("computing cluster percentiles...")
    _, splits, cluster_ids = load_cluster_data(clusters_file)
    _, skills, stats = load_stats_data(stats_file)

    # Change missing values from -1 to Nan.
    stats = stats.astype('float')
    stats[stats < 0] = np.nan

    print("computing cluster sizes...")
    cluster_sizes = {split: defaultdict(int) for split in splits}
    for player_clusters in tqdm(cluster_ids):
        for split, cluster_id in zip(splits, player_clusters):
            cluster_sizes[split][cluster_id] += 1

    for split, sizes_dict in cluster_sizes.items():
        sizes_array = np.zeros(max(sizes_dict.keys()), dtype='int')
        for cluster_id, size in sizes_dict.items():
            sizes_array[cluster_id - 1] = size

        cluster_sizes[split] = sizes_array

    # Compute quartiles for each cluster as summary statistics.
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
            cluster_inds = cluster_ids[:, s] == i + 1  # cluster IDs start from 1
            cluster_points = dataset[cluster_inds]
            for j, p in enumerate(percentiles):

                # A good number of clusters have one or more nan columns. This is
                # because accounts in the cluster had one or more skills below the
                # threshold to have that skill's data included in the official OSRS
                # hiscores. We use np.nanpercentile and pass any nan columns on.
                result[i, j, :] = np.nanpercentile(cluster_points, axis=0, q=p)

        cluster_quartiles[split] = result

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

    out = {
        'cluster_sizes': cluster_sizes,
        'cluster_quartiles': cluster_quartiles,
        'cluster_uniqueness': cluster_uniqueness
    }
    with open(out_file, 'wb') as f:
        pickle.dump(out, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
