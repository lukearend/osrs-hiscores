#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3d using UMAP.
    Full grid search over 3 splits, 16 parameter sets takes 10 mins.
"""

import pickle
import time
import sys

from src.common import skill_splits, load_centroid_data
from src.models import umap_params, umap_reduce


def main(in_file: str, out_file: str, params_file: str = None):
    """
    :param in_file: load cluster centroids from this file
    :param out_file: serialize results to this file
    :param params_file: load UMAP parameters from this file
                        (if not provided, uses default location)
    """
    centroids = load_centroid_data(in_file)

    print("computing 3d embeddings...")
    splits = skill_splits()
    params = umap_params(params_file)
    njobs = len(splits) * len(params['n_neighbors']) * len(params['min_dist'])

    xyz = {}
    job_i = 0
    for split in splits:
        xyz[split.name] = {}
        for n_neighbors in params['n_neighbors']:
            xyz[split.name][n_neighbors] = {}
            for min_dist in params['min_dist']:
                progress = f"{job_i + 1}/{njobs}".ljust(8)
                print(f"{progress} running split '{split.name}' "
                      f"(n_neighbors = {n_neighbors}, min_dist = {min_dist:.2f})... ", end='', flush=True)

                t0 = time.time()
                X = centroids[split.name]
                u = umap_reduce(X, d=3, n_neighbors=n_neighbors, min_dist=min_dist)
                print(f"done ({time.time() - t0:.2f} sec)")

                xyz[split.name][n_neighbors][min_dist] = u
                job_i += 1

    with open(out_file, 'wb') as f:
        pickle.dump(xyz, f)

    print("saved results to file")


if __name__ == '__main__':
    main(*sys.argv[1:])
