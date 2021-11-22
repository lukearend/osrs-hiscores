#!/usr/bin/env python3

""" Compute percentile-based centroids for each cluster. """

import pickle

import numpy as np
from tqdm import tqdm


STATS_FILE = '../../data/processed/stats.pkl'
CLUSTERS_FILE = '../../data/processed/clusters.pkl'
OUT_FILE = '../../data/processed/centroids.pkl'


def main():
    print('loading player stats...')
    with open(STATS_FILE, 'rb') as f:
        contents = pickle.load(f)

    players = contents['usernames']
    skills = np.array(contents['stats'][:, 4::3], dtype='float32')
    skills[skills < 0] = np.nan

    with open(CLUSTERS_FILE, 'rb') as f:
        contents = pickle.load(f)

    results = {}
    for split, result in contents.items():
        num_clusters = result['num_clusters']

        print("processing split '{}'".format(split))

        if split == 'all':
            dataset = skills
            cluster_centroids = np.zeros((num_clusters, 23, 3))
        elif split == 'cb':
            dataset = skills[:, :7]
            cluster_centroids = np.zeros((num_clusters, 7, 3))
        else:
            dataset = skills[:, 7:]
            cluster_centroids = np.zeros((num_clusters, 16, 3))

        for i in tqdm(range(num_clusters)):
            keep_inds = result['cluster_ids'] == i + 1
            cluster_rows = dataset[keep_inds]
            cluster_centroids[i, :, 0] = np.nanpercentile(cluster_rows, axis=0, q=5)
            cluster_centroids[i, :, 1] = np.nanpercentile(cluster_rows, axis=0, q=50)
            cluster_centroids[i, :, 2] = np.nanpercentile(cluster_rows, axis=0, q=95)

        results[split] = {
            5: cluster_centroids[:, :, 0],
            50: cluster_centroids[:, :, 1],
            95: cluster_centroids[:, :, 2]
        }

    print("handling missing data")
    for split in ['all', 'cb', 'noncb']:
        for percentile in [5, 50, 95]:
            replace_rows, replace_cols = np.isnan(results[split][percentile]).nonzero()
            for i, j in zip(replace_rows, replace_cols):
                results[split][percentile][i, j] = 1
                print("replaced {} percentile {} row: {} col: {} with 1"
                      .format(split, percentile, i, j))

    with open(OUT_FILE, 'wb') as f:
        pickle.dump(results, f)

    print('done')


if __name__ == '__main__':
    main()
