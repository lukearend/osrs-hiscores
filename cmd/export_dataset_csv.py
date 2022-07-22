#!/usr/bin/env python3

""" Export player stats, cluster IDs, and cluster centroids to CSV. """

import os
from src.analysis.io import load_pkl, export_players_csv, export_clusterids_csv, export_centroids_csv

centroids_pkl = os.environ['CLUSTER_CENTROIDS_FILE']
centroids_csv = os.environ['CLUSTER_CENTROIDS_CSV']
clusterids_pkl = os.environ['CLUSTER_CENTROIDS_FILE']
clusterids_csv = os.environ['CLUSTER_CENTROIDS_CSV']
stats_pkl = os.environ['CLUSTER_CENTROIDS_FILE']
stats_csv = os.environ['CLUSTER_CENTROIDS_CSV']

print(f"exporting cluster centroids to csv...")
export_centroids_csv(load_pkl(centroids_pkl), centroids_csv)
print(f"exporting cluster IDs to csv...")
export_clusterids_csv(load_pkl(clusterids_pkl), clusterids_csv)
print(f"exporting player stats to csv...")
export_players_csv(load_pkl(stats_pkl), stats_csv)
print("done")
