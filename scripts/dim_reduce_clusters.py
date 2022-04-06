#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3d using UMAP.
    Full grid search over 3 splits, 16 parameter sets takes 10 mins.
"""
import argparse

import pandas as pd

from src.analytics.models import umap_reduce


def main(centroids_df: pd.DataFrame, n_neighbors: int, min_dist: float) -> pd.DataFrame:

    print(f"running UMAP (n_neighbors = {n_neighbors}, min_dist = {min_dist:.2f})... ", end='', flush=True)

    # todo: centroids_df to np array

    # todo: use CodeTimer with done statement?
    # "done ({:.2f} sec)")

    X = centroids
    u = umap_reduce(X, d=3, n_neighbors=n_neighbors, min_dist=min_dist)

    # todo: np array to xyz_df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Reduce dimensionality of cluster centroids to 3D.""")
    parser.add_argument('infile', type=str, help="load clusters centroids from this CSV file")
    parser.add_argument('outfile', type=str, help="serialize results to this .pkl file")
    parser.add_argument('-p', '--params', type=str, required=False,
                        help="load UMAP parameters from this file (if not provided, uses default location")
    args = parser.parse_args()
    main(args.infile, args.outfile, args.params)
