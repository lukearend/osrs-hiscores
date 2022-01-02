#!/usr/bin/env python3

""" Augment raw clustering results by computing per-cluster metrics. """

import pickle
import sys

import numpy as np


def main(in_file, out_file):
    print("processing cluster data...")

    with open(in_file, 'rb') as f:
        raw_data = pickle.load(f)

    results = {}
    for split, cluster_ids in raw_data.items():
        print("processing split '{}'".format(split))

        num_clusters = np.max(cluster_ids) + 1
        cluster_sizes, _ = np.histogram(cluster_ids, num_clusters)

        results[split] = {
            'cluster_ids': cluster_ids,
            'num_clusters': num_clusters,
            'cluster_sizes': cluster_sizes
        }

        # An account's 'percent uniqueness' is the fraction of players, out of
        # the whole player base, who are as unique or less unique than the
        # given account. 'Uniqueness' is measured by lining up all clusters
        # left to right in an ordering such that the smallest clusters (those
        # with fewest players) are on the left, the clusters are monotonically
        # increasing in size, and the largest cluster is on the right. Player
        # A's percent uniqueness is the number of players in clusters with the
        # same or greater size than player A's cluster, divided by the total
        # number of players.

        sorted_inds = np.argsort(cluster_sizes)
        sorted_cluster_sizes = cluster_sizes[sorted_inds]
        uniqueness_scores = np.cumsum(sorted_cluster_sizes[::-1])[::-1]

        num_players = len(cluster_ids)
        uniqueness_percentiles = {}
        for size in sorted_cluster_sizes:
            if size in uniqueness_percentiles:
                continue

            keep_inds = (sorted_cluster_sizes == size).nonzero()[0]
            num_less_unique_players = uniqueness_scores[keep_inds[0]]
            uniqueness_percentile = num_less_unique_players / num_players
            uniqueness_percentiles[size] = uniqueness_percentile

        cluster_uniqueness = np.zeros(num_clusters)
        for i, cluster_size in enumerate(sorted_cluster_sizes):
            cluster_id = sorted_inds[i]
            cluster_uniqueness[cluster_id] = uniqueness_percentiles[cluster_size]

        results[split]['percent_uniqueness'] = np.array(cluster_uniqueness)

    with open(out_file, 'wb') as f:
        pickle.dump(results, f)


if __name__ == '__main__':
    main(*sys.argv[1:])
