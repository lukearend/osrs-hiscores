#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3D using UMAP. """
import argparse
from collections import OrderedDict

import pandas as pd

from src.analysis.data import load_pkl, dump_pkl
from src.analysis.models import umap_reduce


def main(centroids: OrderedDict[str, pd.DataFrame],
         n_neighbors: int, min_dist: float) -> OrderedDict[str, pd.DataFrame]:

    xyz = {}
    for split, split_centroids in centroids.items():
        print(f"running dimensionality reduction for split '{split}'...")
        split_xyz = umap_reduce(split_centroids.to_numpy(), 3, n_neighbors, min_dist)
        split_xyz = pd.DataFrame(split_xyz, index=split_centroids.index, columns=('x', 'y', 'z'))
        xyz[split] = split_xyz

    return xyz


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reduce dimensionality of cluster centroids to 3D.")
    parser.add_argument('--in-file', type=str, help="load clusters centroids from this file")
    parser.add_argument('--out-file', type=str, help="write cluster xyz coordinates to this file")
    parser.add_argument('-n', '--n-neighbors', type=int, help="UMAP n_neighbors parameter")
    parser.add_argument('-m', '--min-dist', type=float, help="UMAP min_dist parameter")
    args = parser.parse_args()

    centroids_dict = load_pkl(args.in_file)
    xyz_dict = main(centroids_dict, args.n_neighbors, args.min_dist)
    dump_pkl(xyz_dict, args.out_file)
    print(f"wrote cluster xyz coordinates to {args.out_file}")
