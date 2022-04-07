#!/usr/bin/env python3

import argparse


def main(centroids_file: str, cluster_analytics_file: str, clusters_xyz_file: str, out_file: str,
         mongo_url: str, coll_name: str, drop: bool = False):
    pass


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
