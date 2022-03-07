#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3d using UMAP.
    Full grid search over 3 splits, 16 parameter sets takes 10 mins.
"""
import argparse
import pickle
import time
import sys

from codetiming import Timer

from src.common import skill_splits, load_centroid_data
from src.models import load_umap_params, umap_reduce


@Timer(text="finished dimensionality reduction (total time {:.2f} sec)")
def main(in_file: str, out_file: str, params_file: str = None):
    centroids = load_centroid_data(in_file)

    print("computing 3d embeddings...")
    splits = skill_splits()
    params = load_umap_params(params_file)
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
    parser = argparse.ArgumentParser(description="""Reduce dimensionality of cluster centroids to 3D.""")
    parser.add_argument('infile', type=str, help="load clusters centroids from this CSV file")
    parser.add_argument('outfile', type=str, help="serialize results to this .pkl file")
    parser.add_argument('-p', '--params', type=str, required=False,
                        help="load UMAP parameters from this file (if not provided, uses default location")
    args = parser.parse_args()
    main(args.infile, args.outfile, args.params)
