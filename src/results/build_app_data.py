#!/usr/bin/env python3

""" Preprocess and build a single file for the data to be used in Dash app. """
import pickle
import sys

import numpy as np

from src.common import skill_splits, load_centroid_data
from src.results import AppData, SplitData, ClusterData, load_cluster_analytics, load_clusters_xyz


def compute_minmax(xyz):
    return {
        'x': (np.min(xyz[:, 0]), np.max(xyz[:, 0])),
        'y': (np.min(xyz[:, 1]), np.max(xyz[:, 1])),
        'z': (np.min(xyz[:, 2]), np.max(xyz[:, 2]))
    }


def main(centroids_file: str, cluster_analytics_file: str, clusters_xyz_file: str, out_file: str):
    """
    :param centroids_file: load cluster centroids from this file
    :param cluster_analytics_file: load cluster analytics from this file
    :param clusters_xyz_file: load cluster dimensionality reduction output from this file
    :param out_file: serialize app data to this file
    """
    print("building app data...", end=' ', flush=True)
    cluster_analytics = load_cluster_analytics(cluster_analytics_file)
    cluster_xyz = load_clusters_xyz(clusters_xyz_file)
    centroids = load_centroid_data(centroids_file)

    splits = skill_splits()
    results = {}
    for split in splits:
        cluster_data = ClusterData(
            xyz=cluster_xyz[split.name],
            sizes=cluster_analytics[split.name].sizes,
            centroids=centroids[split.name],
            quartiles=cluster_analytics[split.name].quartiles,
            uniqueness=cluster_analytics[split.name].uniqueness
        )

        axlims = {}
        for n_neighbors, nn_dict in cluster_xyz[split.name].items():
            axlims[n_neighbors] = {}
            for min_dist in nn_dict.keys():
                xyz = cluster_xyz[split.name][n_neighbors][min_dist]
                axlims[n_neighbors][min_dist] = compute_minmax(xyz)

        split_results = SplitData(
            skills=split.skills,
            clusterdata=cluster_data,
            axlims=axlims
        )
        results[split.name] = split_results

    app_data = AppData(
        splitnames=[s.name for s in splits],
        splitdata=results
    )

    with open(out_file, 'wb') as f:
        pickle.dump(app_data, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
