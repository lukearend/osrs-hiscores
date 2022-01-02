#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3d using UMAP. """

import json
import pathlib
import pickle
import time
import sys

import numpy as np
import umap


def main(clusters_file, percentiles_file, out_file):
    with open(clusters_file, 'rb') as f:
        cluster_data = pickle.load(f)

    with open(percentiles_file, 'rb') as f:
        percentiles = pickle.load(f)

    # These parameters were found by manually inspecting clusterings
    # of the data for all parameter combinations in a grid search over
    # n_neighbors = [5, 10, 15, 20] and min_dist = [0.0, 0.1, 0.25, 0.5],
    # and choosing the parameter set that qualitatively "looked best"--
    # i.e. is best spread out and brings out the most structure. For
    # more info and visual explanations of the UMAP parameters, see
    # https://umap-learn.readthedocs.io/en/latest/parameters.html.

    params_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/umap_params.json'
    with open(params_file, 'r') as f:
        params = json.load(f)

    print("computing 3d embeddings...")

    results = {}
    for split, p in params.items():

        n_neighbors = p['n_neighbors']
        min_dist = p['min_dist']

        print("reducing dimensionality for split '{}'".format(split))
        print("UMAP parameters: n_neighbors = {}, min_dist = {:.2f}"
              .format(n_neighbors, min_dist))
        print("running... ", end='', flush=True)

        # Null columns are due to missing hiscores data from unranked skills.
        # Replace these with 1 (as in skill level 1) for embedding purposes.

        centroids = percentiles[split][50][:, 1:]    # 50th percentile (median)
        centroids = np.nan_to_num(centroids, nan=1.0)

        # For reproducibility.
        np.random.seed(0)
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

    with open(out_file, 'wb') as f:
        pickle.dump(results, f)

    print("saved results to file")


if __name__ == '__main__':
    main(*sys.argv[1:])
