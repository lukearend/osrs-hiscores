""" Cluster players according to account similarity. """

import argparse
from collections import OrderedDict
from typing import Tuple, List, Dict

import numpy as np
import pandas as pd

from src.analysis.data import load_pkl, dump_pkl
from src.analysis.models import fit_kmeans, cluster_l2
from src.analysis import load_splits


def main(players: pd.DataFrame, nclusters: int,
         splits: OrderedDict[str, List[str]],
         verbose: bool = True) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:

    unames = players.index
    centroids_per_split = OrderedDict()
    clusterids = np.zeros((len(players), len(splits)), dtype='int')

    for i, (split, skills) in enumerate(splits.items()):
        print(f"clustering split {split}...")
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
    parser.add_argument('-i', '--in-file', type=str, help="load player stats from this file")
    parser.add_argument('-k', '--n-clusters', type=int, required=True, help="number of clusters")
    parser.add_argument('-v', '--verbose', action='store_true', help="if set, output progress during training")
    parser.add_argument('--out-clusterids', type=str, help="write cluster IDs to this file")
    parser.add_argument('--out-centroids', type=str, help="write cluster centroids to this file")
    args = parser.parse_args()

    players_df = load_pkl(args.in_file)
    clusterids_df, centroids_dict = main(players_df, nclusters=args.n_clusters, splits=load_splits(), verbose=args.verbose)
    dump_pkl(clusterids_df, args.out_clusterids)
    print(f"wrote player cluster IDs to {args.out_clusterids}")
    dump_pkl(centroids_dict, args.out_centroids)
    print(f"wrote cluster centroids to {args.out_clusterids}")
