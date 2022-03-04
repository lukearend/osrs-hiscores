#!/usr/bin/env python3

""" Compute size, quartiles and uniqueness for each cluster.
    This script runs in about ~5 mins on an M1 Mac.
"""
import argparse
import pickle
import sys

import numpy as np
from codetiming import Timer
from tqdm import tqdm

from src.common import skill_splits, split_dataset, load_clusterids_data, load_stats_data
from src.results import ClusterAnalytics, compute_cluster_sizes, compute_cluster_uniqueness, compute_skill_quartiles


@Timer(text="done postprocessing clusters ({:.2f} sec)")
def main(stats_file: str, clusters_file: str, out_file: str):
    _, splits, clusterids = load_clusterids_data(clusters_file)
    print("computing cluster sizes...")
    cluster_sizes = {}
    for s, split in enumerate(splits):
        cluster_sizes[split] = compute_cluster_sizes(clusterids[:, s])

    print("computing cluster uniqueness...")
    cluster_uniqueness = {}
    for split in splits:
        cluster_uniqueness[split] = compute_cluster_uniqueness(cluster_sizes[split])

    splits = skill_splits()
    _, skills, stats = load_stats_data(stats_file)
    stats = stats.astype('float')
    stats[stats < 0] = np.nan  # change missing values from -1 to nan

    cluster_quartiles = {}
    for s, split in enumerate(splits):
        nclusters = len(cluster_sizes[split.name])
        print(f"computing quartiles for split '{split.name}'...")
        quartiles = np.zeros((nclusters, 5, split.nskills))
        player_vectors = split_dataset(stats, split)

        for cid in tqdm(range(nclusters)):
            id_locs = clusterids[:, s] == cid
            vectors_in_cluster = player_vectors[id_locs]
            quartiles[cid, :, :] = compute_skill_quartiles(vectors_in_cluster)
        cluster_quartiles[split.name] = quartiles

    analytics_per_split = {}
    for split in splits:
        analytics = ClusterAnalytics(
            sizes=cluster_sizes[split.name],
            quartiles=cluster_quartiles[split.name],
            uniqueness=cluster_uniqueness[split.name]
        )
        analytics_per_split[split.name] = analytics

    with open(out_file, 'wb') as f:
        pickle.dump(analytics_per_split, f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Compute cluster sizes, quartiles and uniqueness.""")
    parser.add_argument('statsfile', type=str, help="load player stats from this CSV file")
    parser.add_argument('clustersfile', type=str, help="load player clusters from this CSV file")
    parser.add_argument('outfile', type=str, help="serialize results to this .pkl file")
    args = parser.parse_args()
    main(args.statsfile, args.centroidsfile, args.paramsfile)
