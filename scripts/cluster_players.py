#!/usr/bin/env python3

""" Cluster players according to account similarity. """

import argparse
import collections
from typing import Tuple, List, Dict, OrderedDict

import numpy as np
import pandas as pd

from src.analysis.data import load_pkl, dump_pkl, load_json
from src.analysis.models import fit_kmeans, cluster_l2


def main(players: pd.DataFrame,
         splits: OrderedDict[str, List[str]],
         k_per_split: OrderedDict[str, int],
         verbose: bool = True) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:

    unames = players.index
    centroids_per_split = collections.OrderedDict()
    clusterids = np.zeros((len(players), len(splits)), dtype='int')

    for i, (split, skills) in enumerate(splits.items()):
        nclusters = k_per_split[split]
        print(f"clustering split '{split}' with k = {nclusters}...")
        stats = players[skills]  # take a subset of skills as features
        stats = stats.to_numpy()

        # Player weight is proportional to the number of ranked skills.
        weights = np.sum(stats != 0, axis=1) / stats.shape[1]

        # Replace missing data, i.e. unranked stats, with 1s. This is
        # a reasonable substitution for clustering purposes since an
        # unranked stat is known to be relatively low.
        stats[stats == 0] = 1
        centroids = fit_kmeans(stats, k=nclusters, w=weights, verbose=verbose)

        # Sort clusters by total level descending.
        total_levels = np.sum(centroids, axis=1)
        sort_inds = np.argsort(total_levels)[::-1]
        centroids = centroids[sort_inds]

        clusterids[:, i] = cluster_l2(stats, centroids)
        centroids = pd.DataFrame(centroids, index=range(nclusters), columns=skills)
        centroids_per_split[split] = centroids

    clusterids = pd.DataFrame(clusterids, index=unames, columns=splits.keys())

    return clusterids, centroids_per_split


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cluster players according to account similarity.")
    parser.add_argument('--in-file', required=True, type=str, help="load player stats from this file")
    parser.add_argument('--out-clusterids', required=True, type=str, help="write cluster IDs to this file")
    parser.add_argument('--out-centroids', required=True, type=str, help="write cluster centroids to this file")
    parser.add_argument('--params-file', required=True, type=str, help="load clustering parameters from this file")
    parser.add_argument('--splits-file', required=True, type=str, help="load skills in each split from this file")
    parser.add_argument('--verbose', action='store_true', help="if set, output progress during training")
    args = parser.parse_args()

    splits = load_json(args.splits_file)
    k_per_split = {split: params['k'] for split, params in load_json(args.params_file).items()}
    for split in splits.keys():
        if split not in k_per_split:
            raise ValueError(f"params file is missing k parameter for split '{split}'")

    players_df = load_pkl(args.in_file)
    clusterids_df, centroids_dict = main(players_df,
                                         k_per_split=k_per_split,
                                         splits=load_json(args.splits_file),
                                         verbose=args.verbose)

    dump_pkl(clusterids_df, args.out_clusterids)
    print(f"wrote player cluster IDs to {args.out_clusterids}")
    dump_pkl(centroids_dict, args.out_centroids)
    print(f"wrote cluster centroids to {args.out_clusterids}")
