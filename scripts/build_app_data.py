#!/usr/bin/env python3

""" Build clustering results file for main application. """

import argparse
import collections
from typing import List, OrderedDict

import pandas as pd
import xarray as xr

from src.data.analytics import get_cluster_sizes, get_cluster_uniqueness
from src.data.io import load_pkl, dump_pkl, load_json
from src.data.types import SplitResults


def main(splits: OrderedDict[str, List[str]],
         clusterids: pd.DataFrame,
         centroids: OrderedDict[str, pd.DataFrame],
         quartiles: OrderedDict[str, xr.DataArray],
         xyz: OrderedDict[str, pd.DataFrame]) -> OrderedDict[str, SplitResults]:

    app_data = collections.OrderedDict()
    for split, skills_in_split in splits.items():
        cluster_xyz = xyz[split]
        cluster_sizes = get_cluster_sizes(clusterids[split])
        split_data = SplitResults(
            skills=skills_in_split,
            cluster_quartiles=quartiles[split],
            cluster_centroids=centroids[split],
            cluster_xyz=cluster_xyz,
            cluster_sizes=cluster_sizes.astype('int'),
            cluster_uniqueness=get_cluster_uniqueness(cluster_sizes),
            xyz_axlims={
                'x': (min(cluster_xyz['x']), max(cluster_xyz['x'])),
                'y': (min(cluster_xyz['y']), max(cluster_xyz['y'])),
                'z': (min(cluster_xyz['z']), max(cluster_xyz['z']))
            })
        app_data[split] = split_data

    return app_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build data file and database for application to use.")
    parser.add_argument('--splits-file', required=True, help="load skills in each split from this file")
    parser.add_argument('--clusterids-file', required=True, help="load player cluster IDs from this file")
    parser.add_argument('--centroids-file', required=True, help="load cluster centroids from this file")
    parser.add_argument('--quartiles-file', required=True, help="load cluster quartiles from this file")
    parser.add_argument('--xyz-file', required=True, help="load cluster 3D coordinates from this file")
    parser.add_argument('--out-file', required=True, help="write application data object to this file")
    args = parser.parse_args()

    print("building app data file...")

    splits = load_json(args.splits_file)
    clusterids_df = load_pkl(args.clusterids_file)
    centroids_dict = load_pkl(args.centroids_file)
    quartiles_dict = load_pkl(args.quartiles_file)
    xyz_dict = load_pkl(args.xyz_file)
    appdata = main(splits, clusterids_df, centroids_dict, quartiles_dict, xyz_dict)

    dump_pkl(appdata, args.out_file)
    print(f"wrote app data to {args.out_file}")
