#!/usr/bin/env python3

""" Reduce dimensionality of cluster centroids to 3D using UMAP. """

import argparse
from collections import OrderedDict

import pandas as pd

from src.analysis import load_splits
from src.analysis.data import load_pkl, dump_pkl, load_json
from src.analysis.models import umap_reduce


def main(centroids: OrderedDict[str, pd.DataFrame],
         n_neighbors: OrderedDict[str, int],
         min_dist: OrderedDict[str, float]) -> OrderedDict[str, pd.DataFrame]:

    xyz = {}
    for split, split_centroids in centroids.items():
        nn = n_neighbors[split]
        mindist = min_dist[split]
        print(f"reducing dimensionality for split '{split}' (n_neighbors = {nn}, min_dist = {mindist})...")
        split_xyz = umap_reduce(split_centroids.to_numpy(), d=3, n_neighbors=nn, min_dist=mindist)
        split_xyz = pd.DataFrame(split_xyz, index=split_centroids.index, columns=('x', 'y', 'z'))
        xyz[split] = split_xyz

    return xyz


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reduce dimensionality of cluster centroids to 3D.")
    parser.add_argument('--in-file', required=True, type=str, help="load clusters centroids from this file")
    parser.add_argument('--out-file', required=True, type=str, help="write cluster xyz coordinates to this file")
    parser.add_argument('--params-file', type=str, help="load parameters to use for each split from this file")
    args = parser.parse_args()


    nn_per_split = {split: params['n_neighbors'] for split, params in load_json(args.params_file).items()}
    mindist_per_split = {split: params['min_dist'] for split, params in load_json(args.params_file).items()}
    centroids_dict = load_pkl(args.in_file)
    for split in centroids_dict.keys():
        if split not in nn_per_split:
            raise ValueError(f"params file is missing n_neighbors parameter for split '{split}'")
        if split not in mindist_per_split:
            raise ValueError(f"params file is missing min_dist parameter for split '{split}'")

    xyz_dict = main(centroids_dict, nn_per_split, mindist_per_split)
    dump_pkl(xyz_dict, args.out_file)
    print(f"wrote cluster xyz coordinates to {args.out_file}")
