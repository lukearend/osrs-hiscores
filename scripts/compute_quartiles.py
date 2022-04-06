#!/usr/bin/env python3

""" Compute size, quartiles and uniqueness for each
cluster. This script runs in about ~5 mins on an M1 Mac. """

import argparse
import pickle

import numpy as np
from tqdm import tqdm


def main(players_df: pd.DataFrame, clusterids: NDArray, use_skills: List[str] = None) -> pd.DataFrame:

    stats = stats.astype('float')  # cast to float so we can use nan
    stats[stats < 0] = np.nan      # change missing values from -1 to nan
    total_levels, stats = stats[:, 0], stats[:, 1:]

    nclusters = len(cluster_sizes[split.name])
    quartiles = np.zeros((nclusters, 5, 1 + split.nskills))
    player_vectors = split_dataset(stats, split.name)

    for cid in tqdm(range(nclusters)):
        id_locs = clusterids[:, s] == cid  # inds for players with this cluster ID
        pvectors = player_vectors[id_locs, :]
        totlevels = np.expand_dims(total_levels[id_locs], 1)
        cluster_data = np.concatenate([totlevels, pvectors], axis=1)
        quartiles[cid, :, :] = compute_stat_quartiles(cluster_data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Compute cluster sizes, quartiles and uniqueness.""")
    parser.add_argument('stats_file', type=str, help="load player stats from this file")
    parser.add_argument('clusterids_file', type=str, help="load player clusters from this file")
    parser.add_argument('out_file', type=str, help="write cluster quartiles to this file")
    args = parser.parse_args()

    # todo: read stats file
    # todo: read clusterids_file
    # todo: read split file and iterate through splits
    # todo: dump quartiles_file
