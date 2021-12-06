#!/usr/bin/env python3

""" Compute percentile-based centroids for each cluster. """

import pickle
import sys

import numpy as np
from tqdm import tqdm


def main(stats_file, clusters_file, out_file):
    print("loading player data...")
    with open(stats_file, 'rb') as f:
        contents = pickle.load(f)
        players = contents['usernames']
        skills = np.array(contents['stats'][:, 1::3], dtype='float32')

    skills[skills < 0] = np.nan

    with open(clusters_file, 'rb') as f:
        clusters = pickle.load(f)

    print("computing cluster percentiles...")
    percentiles = [0, 25, 50, 75, 100]

    results = {}
    for split, result in clusters.items():
        num_clusters = result['num_clusters']

        print("processing split '{}'".format(split))

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
            for p in percentiles:
                cluster_centroids[cluster_id, :, p] = np.nanpercentile(cluster_rows, axis=0, q=p)

        results[split] = {p: cluster_centroids[:, :, i] for i, p in enumerate(percentiles)}

    print("handling missing data")
    for split in clusters.keys():
        for p in percentiles:
            replace_rows, replace_cols = np.isnan(results[split][p]).nonzero()
            for i, j in zip(replace_rows, replace_cols):
                results[split][percentile][i, j] = 1
                print("replaced {} percentile {} row: {} col: {} with 1"
                      .format(split, percentile, i, j))

    with open(out_file, 'wb') as f:
        pickle.dump(results, f)

    print('done')


if __name__ == '__main__':
    main(*sys.argv[1:])
