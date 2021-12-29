#!/usr/bin/env python3

""" Compute percentile-based centroids for each cluster. """

import pickle
import sys

import numpy as np
from tqdm import tqdm


def main(stats_file, clusters_file, out_file):
    print("computing cluster percentiles...")
    percentiles = [0, 25, 50, 75, 100]

    print("loading player data...")
    with open(stats_file, 'rb') as f:
        stats_data = pickle.load(f)
        players = stats_data['usernames']
        skills = np.array(stats_data['stats'][:, 1::3], dtype='float32')

    skills[skills < 0] = np.nan

    with open(clusters_file, 'rb') as f:
        cluster_data = pickle.load(f)

    results = {}
    for split, result in cluster_data.items():

        print("processing split '{}'".format(split))
        num_clusters = result['num_clusters']

        if split == 'all':
            dataset = skills
            cluster_centroids = np.zeros((num_clusters, 24, len(percentiles)))
        elif split == 'cb':
            dataset = skills[:, :8]
            cluster_centroids = np.zeros((num_clusters, 8, len(percentiles)))
        else:
            dataset = np.concatenate([np.expand_dims(skills[:, 0], axis=1), skills[:, 8:]], axis=1)
            cluster_centroids = np.zeros((num_clusters, 17, len(percentiles)))

        for cluster_id in tqdm(range(num_clusters)):
            keep_inds = result['cluster_ids'] == cluster_id
            cluster_rows = dataset[keep_inds]
            for i, p in enumerate(percentiles):

                # A good number of clusters have one or more nan columns. This is
                # because accounts in the cluster had one or more skills below the
                # threshold to have that skill's data included in the official OSRS
                # hiscores. We use np.nanpercentile and pass any nan columns on.

                cluster_centroids[cluster_id, :, i] = np.nanpercentile(cluster_rows, axis=0, q=p)

        results[split] = {percent: cluster_centroids[:, :, i]
                          for i, percent in enumerate(percentiles)}

    print("handling missing data")
    for split in cluster_data.keys():
        for percent in percentiles:
            replace_rows, replace_cols = np.isnan(results[split][percent]).nonzero()
            for row_i, col_i in zip(replace_rows, replace_cols):
                results[split][percent][row_i, col_i] = 1
                print("replaced '{}' {}th percentile row: {} col: {} with 1"
                      .format(split, percent, row_i, col_i))

    with open(out_file, 'wb') as f:
        pickle.dump(results, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
