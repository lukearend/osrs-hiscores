#!/usr/bin/env python3

""" Compute size, quartiles and uniqueness for each cluster.
    This script runs in about ~5 mins on an M1 Mac.
"""

import pickle
import sys

import numpy as np
from tqdm import tqdm

from src import load_skill_splits, load_clusterids_data, load_stats_data, split_dataset
from src import compute_cluster_sizes, compute_cluster_uniqueness, compute_skill_quartiles


def main(stats_file, clusters_file, out_file):
    _, splits, clusterids = load_clusterids_data(clusters_file)
    print("computing cluster sizes...")
    cluster_sizes = {}
    for s, split in splits:
        cluster_sizes[split] = compute_cluster_sizes(clusterids[:, s])

    print("computing cluster uniqueness...")
    cluster_uniqueness = {}
    for split in splits:
        cluster_uniqueness[split] = compute_cluster_uniqueness(cluster_sizes[split])

    splits = load_skill_splits()
    _, skills, stats = load_stats_data(stats_file)
    stats = stats.astype('float')
    stats[stats < 0] = np.nan  # change missing values from -1 to nan

    cluster_quartiles = {}
    nclusters = len(cluster_sizes)
    for s, split in enumerate(splits):
        print(f"computing quartiles for split '{split.name}'...")
        quartiles = np.zeros((nclusters, 5, split.nskills))
        player_vectors = split_dataset(stats)

        for cid in tqdm(range(nclusters)):
            id_locs = clusterids[:, s] == cid
            vectors_in_cluster = player_vectors[id_locs]
            quartiles[cid, :, :] = compute_skill_quartiles(vectors_in_cluster)

        cluster_quartiles[split] = quartiles

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
