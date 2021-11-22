#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3d using UMAP. """

import json
import pickle
import time

import numpy as np
import umap


CLUSTERS_FILE = '../../data/processed/clusters.pkl'
CENTROIDS_FILE = '../../data/processed/centroids.pkl'
PARAMS_FILE = '../../reference/umap_params.json'
OUT_FILE = '../../data/processed/dimreduced.pkl'


def main():
    with open(CLUSTERS_FILE, 'rb') as f:
        cluster_data = pickle.load(f)

    with open(CENTROIDS_FILE, 'rb') as f:
        centroid_data = pickle.load(f)

    # These parameters were found by manually inspecting clusterings
    # of the data for all parameter combinations in a grid search over
    # n_neighbors = [5, 10, 15, 20] and min_dist = [0.0, 0.1, 0.25, 0.5],
    # and choosing the parameter set that qualitatively "looked best"--
    # i.e. is best spread out and brings out the most structure. For
    # more info and visual explanations of the UMAP parameters, see
    # https://umap-learn.readthedocs.io/en/latest/parameters.html.

    with open(PARAMS_FILE, 'r') as f:
        params = json.load(f)

    # For reproducibility.
    np.random.seed(0)

    results = {}
    for split, p in params.items():

        n_neighbors = p['n_neighbors']
        min_dist = p['min_dist']

        print("reducing dimensionality for split '{}'".format(split))
        print("UMAP parameters: n_neighbors = {}, min_dist = {:.2f}"
              .format(n_neighbors, min_dist))
        print("running... ", end='', flush=True)

        centroids = centroid_data[split][50]    # 50th percentile (median)
        cluster_sizes = cluster_data[split]['cluster_sizes']

        t0 = time.time()
        fit = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=3,
            metric='euclidean'
        )
        u = fit.fit_transform(centroids)
        elapsed = time.time() - t0

        print("done ({:.2f} sec)".format(elapsed))

        results[split] = u

    with open(OUT_FILE, 'wb') as f:
        pickle.dump(results, f)

    print("saved results to file")


if __name__ == '__main__':
    main()
