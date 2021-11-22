#!/usr/bin/env python3

""" Augment raw clustering results by computing per-cluster metrics. """

import pickle

import numpy as np
from tqdm import tqdm


IN_FILE = '../../data/raw/clusters.pkl'
OUT_FILE = '../../data/processed/clusters.pkl'


def main():
    with open(IN_FILE, 'rb') as f:
        contents = pickle.load(f)

    results = {}
    for split, cluster_ids in contents.items():

        print("processing split '{}'".format(split))

        num_clusters = np.max(cluster_ids)
        cluster_sizes, _ = np.histogram(cluster_ids, num_clusters)

        results[split] = {
            'cluster_ids': cluster_ids,
            'num_clusters': num_clusters,
            'cluster_sizes': cluster_sizes
        }

        sorted_inds = np.argsort(cluster_sizes)
        sorted_cluster_sizes = cluster_sizes[sorted_inds]
        uniqueness_scores = np.cumsum(sorted_cluster_sizes[::-1])[::-1]

        num_players = len(cluster_ids)
        uniqueness_percentiles = {}
        for size in tqdm(sorted_cluster_sizes):
            if size in uniqueness_percentiles:
                continue

            keep_inds = (sorted_cluster_sizes == size).nonzero()[0]
            num_less_unique_players = uniqueness_scores[keep_inds[0]]
            uniqueness_percentile = num_less_unique_players / num_players
            uniqueness_percentiles[size] = uniqueness_percentile

        uniqueness = {}
        for i, cluster_size in enumerate(sorted_cluster_sizes):
            cluster_id = sorted_inds[i] + 1
            uniqueness[cluster_id] = uniqueness_percentiles[cluster_size]
        uniqueness = sorted(uniqueness.items())
        uniqueness = [item[1] for item in uniqueness]

        results[split]['percent_uniqueness'] = np.array(uniqueness)

    with open(OUT_FILE, 'wb') as f:
        pickle.dump(results, f)

    print('done')


if __name__ == '__main__':
    main()
