#!/usr/bin/env python3

""" Preprocess and build a single file for the data to be used in Dash app. """
import pickle
import sys

import numpy as np

from src.common import skill_splits, load_centroid_data
from src.results import AppData, SplitResults, ClusterData


def compute_minmax(xyz):
    return {
        'x': (np.min(xyz[:, 0]), np.max(xyz[:, 0])),
        'y': (np.min(xyz[:, 1]), np.max(xyz[:, 1])),
        'z': (np.min(xyz[:, 2]), np.max(xyz[:, 2]))
    }


def main(centroids_file, cluster_analytics_file, clusters_xyz_file, out_file):
    print("building app data...", end=' ', flush=True)
    with open(cluster_analytics_file, 'rb') as f:
        cluster_analytics = pickle.load(f)
    with open(clusters_xyz_file, 'rb') as f:
        cluster_xyz = pickle.load(f)
    centroids = load_centroid_data(centroids_file)

    splits = skill_splits()
    results = {}
    for split in splits:
        cluster_data = ClusterData(
            xyz=cluster_xyz[split.name],
            sizes=cluster_analytics['sizes'][split.name],
            centroids=centroids[split.name],
            quartiles=cluster_analytics['quartiles'][split.name],
            uniqueness=cluster_analytics['uniqueness'][split.name]
        )

        axlims = {}
        for n_neighbors, nn_dict in cluster_xyz[split.name].items():
            axlims[n_neighbors] = {}
            for min_dist, md_dict in nn_dict.items():
                xyz = cluster_xyz[split.name][n_neighbors][min_dist]
                axlims[n_neighbors][min_dist] = compute_minmax(xyz)

        split_results = SplitResults(
            skills=split.skills,
            clusters=cluster_data,
            axlims=axlims
        )
        results[split.name] = split_results

    app_data = AppData(
        splitnames=[s.name for s in splits],
        results=results
    )

    with open(out_file, 'wb') as f:
        pickle.dump(app_data, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
