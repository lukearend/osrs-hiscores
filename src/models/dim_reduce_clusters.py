#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3d using UMAP. """

import json
import os
import pathlib
import pickle
import time
import sys

import numpy as np
import umap


def main(in_file, out_file):
    with open(in_file, 'rb') as f:
        data = pickle.load(f)

    quartiles = data['cluster_quartiles']
    splits = quartiles.keys()

    centroids = {}
    for split in splits:
        medians = quartiles[split][:, 2, :]         # Centroid is median (50th percentile)
        medians = np.nan_to_num(medians, nan=1.0)   # Set missing data to 1 for embedding purposes.
        centroids[split] = medians

    params_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/umap_params.json'
    with open(params_file, 'r') as f:
        params = json.load(f)

    out_dir = pathlib.Path(__file__).resolve().parents[2] / 'data/raw/dimreduce'
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    print("computing 3d embeddings...")
    num_jobs = len(splits) * len(params['n_neighbors']) * len(params['min_dist'])

    i = 1
    out = {}
    for split in splits:

        out[split] = {}
        for n_neighbors in params['n_neighbors']:

            out[split][n_neighbors] = {}
            for min_dist in params['min_dist']:

                # For reproducibility.
                np.random.seed(0)
                t0 = time.time()

                progress = "{}/{}".format(i, num_jobs).ljust(8)
                print("{} running split '{}' (n_neighbors = {}, min_dist = {:.2f})... "
                      .format(progress, split, n_neighbors, min_dist), end='', flush=True)
                fit = umap.UMAP(
                    n_neighbors=n_neighbors,
                    min_dist=min_dist,
                    n_components=3,
                    metric='euclidean'
                )
                u = fit.fit_transform(centroids[split])

                elapsed = time.time() - t0
                print("done ({:.2f} sec)".format(elapsed))

                out[split][n_neighbors][min_dist] = u
                i += 1

        with open(out_file, 'wb') as f:
            pickle.dump(out, f)

        print("saved results to file")


if __name__ == '__main__':
    main(*sys.argv[1:])
