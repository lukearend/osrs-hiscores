#!/usr/bin/env python3

import argparse
import pickle

import numpy as np

from src.analytics.app import build_app_data
from src.analytics.data import load_pkl


def compute_minmax(xyz):
    return {
        'x': (np.min(xyz[:, 0]), np.max(xyz[:, 0])),
        'y': (np.min(xyz[:, 1]), np.max(xyz[:, 1])),
        'z': (np.min(xyz[:, 2]), np.max(xyz[:, 2]))
    }


def main(centroids_file: str, cluster_analytics_file: str, clusters_xyz_file: str, out_file: str, mongo_url: str, coll_name: str, drop: bool = False):
    # todo: this just computes quartiles




    print("building app data...", end=' ', flush=True)
    cluster_analytics = load_pkl(cluster_analytics_file)
    cluster_xyz = load_pkl(clusters_xyz_file)
    centroids = load_pkl(centroids_file)

    appdata = build_appdata_obj(centroids, cluster_analytics, cluster_xyz)

    with open(out_file, 'wb') as f:
        pickle.dump(app_data, f)

    print("done building app data")

    #####

    print(f"building collection '{coll_name}'")
    print("connecting...", end=' ', flush=True)
    db = connect_mongo(url)
    collection = db[coll_name]
    print("ok")

    build_player_collection






















if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Build app data file and database.""")
    parser.add_argument('centroidsfile', type=str, help="load cluster centroids from this CSV file")
    parser.add_argument('clustersfile', type=str, help="load cluster analytics from this .pkl file")
    parser.add_argument('xyzfile', type=str, help="load results of dimensionality reduction from this .pkl file")
    parser.add_argument('outfile', type=str, help="serialize app data to this .pkl file")
    parser.add_argument('statsfile', type=str, help="load player stats from this CSV file")

    parser.add_argument('clustersfile', type=str, help="load player cluster IDs from this CSV file")
    parser.add_argument('-u', '--url', type=str, default="localhost:27017",
                        help="use Mongo instance running at this URL (defaults to localhost:27017)")
    parser.add_argument('-c', '--coll', type=str, default="players",
                        help="name of collection to populate (default is 'players')")
    parser.add_argument('-d', '--drop', action='store_true',
                        help="if set, will forcibly drop collection before writing (default is unset)")

    args = parser.parse_args()
    main(args.centroidsfile, args.clustersfile, args.xyzfile, args.outfile)
