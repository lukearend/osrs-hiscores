#!/usr/bin/env python3

""" Compute quartiles for each skill across the players in each cluster. """

import argparse
from typing import List, OrderedDict

import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm

from src.analysis.data import load_pkl, dump_pkl, load_json
from src.analysis.results import compute_stat_quartiles


def main(players: pd.DataFrame, clusterids: pd.DataFrame,
         splits: OrderedDict[str, List[str]]) -> OrderedDict[str, xr.DataArray]:

    quartiles = {}
    for split, skills in splits.items():
        skills = ['total'] + skills  # include total level when computing quartiles for each split
        split_stats = players[skills].to_numpy()
        split_clusterids = clusterids[split].to_numpy()
        nclusters = max(split_clusterids) + 1

        print(f"computing quartiles for split '{split}'...")
        split_quartiles = np.zeros((5, nclusters, len(skills)))
        for i in tqdm(range(nclusters)):
            this_cluster_inds = split_clusterids == i
            this_cluster_stats = split_stats[this_cluster_inds]
            split_quartiles[:, i, :] = compute_stat_quartiles(this_cluster_stats)

        split_quartiles = xr.DataArray(
            split_quartiles,
            dims=["percentile", "clusterid", "skill"],
            coords={
                "percentile": [0, 25, 50, 75, 100],
                "clusterid": range(nclusters),
                "skill": skills
            })
        quartiles[split] = split_quartiles

    return quartiles


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Compute stat quantiles for each cluster.")
    parser.add_argument('--stats-file', required=True, type=str, help="load player stats from this file")
    parser.add_argument('--clusterids-file', required=True, type=str, help="load player cluster IDs from this file")
    parser.add_argument('--splits-file', required=True, type=str, help="load skills in each split from this file")
    parser.add_argument('--out-file', required=True, type=str, help="write cluster quartiles to this file")
    args = parser.parse_args()

    players_df = load_pkl(args.stats_file)
    clusterids_df = load_pkl(args.clusterids_file)
    quartiles_dict = main(players_df, clusterids_df, splits=load_json(args.split_file))
    dump_pkl(quartiles_dict, args.out_file)
    print(f"wrote cluster quartiles to {args.out_file}")
