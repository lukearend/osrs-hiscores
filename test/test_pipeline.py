from collections import OrderedDict
from pathlib import Path

import pandas as pd
import xarray as xr

from scripts.cluster_players import main as cluster_players
from scripts.compute_quartiles import main as compute_quartiles
from scripts.dim_reduce_clusters import main as dim_reduce_clusters
# from scripts.build_app_data import main as build_app_data

from src.analysis.data import import_players_csv
from src.analysis import osrs_skills, load_splits

STATS_FILE = Path(__file__).resolve().parent / "data" / "test-data.csv"
SPLITS = OrderedDict([
    ("first5", ["attack", "defence", "strength", "hitpoints", "ranged"]),
    ("last10", ["smithing", "mining", "herblore", "agility", "thieving",
                "slayer", "farming", "runecraft", "hunter", "construction"])
])
NCLUSTERS = 50
UMAP_NN = 5
UMAP_MINDIST = 0.25


global players_df
global clusterids_df, centroids_dict
global quartiles_dict
global xyz_dict


def test_splits():
    for skills_in_split in load_splits().values():
        for skill in skills_in_split:
            assert skill in osrs_skills()


def test_import_csv():
    global players_df
    players_df = import_players_csv(STATS_FILE)
    assert isinstance(players_df, pd.DataFrame)
    assert len(players_df) == 10000
    assert list(players_df.columns) == osrs_skills(include_total=True)


def test_cluster():
    global players_df, clusterids_df, centroids_dict
    clusterids_df, centroids_dict = cluster_players(players_df, k=NCLUSTERS, splits=SPLITS, verbose=False)
    assert isinstance(clusterids_df, pd.DataFrame)
    assert len(clusterids_df) == len(players_df)
    assert tuple(clusterids_df.columns) == tuple(SPLITS.keys())
    for split, skills_in_split in SPLITS.items():
        split_centroids = centroids_dict[split]
        assert isinstance(split_centroids, pd.DataFrame)
        assert list(split_centroids.index) == list(range(NCLUSTERS))
        assert list(split_centroids.columns) == skills_in_split


def test_quartiles():
    global players_df, clusterids_df, quartiles_dict
    quartiles_dict = compute_quartiles(players_df, clusterids_df, SPLITS)
    assert quartiles_dict.keys() == SPLITS.keys()
    for split, split_quartiles in quartiles_dict.items():
        assert isinstance(split_quartiles, xr.DataArray)
        assert list(split_quartiles.dims) == ["percentile", "clusterid", "skill"]
        assert list(split_quartiles.coords["percentile"]) == [0, 25, 50, 75, 100]
        assert list(split_quartiles.coords["clusterid"]) == list(range(NCLUSTERS))
        assert list(split_quartiles.coords["skill"]) == SPLITS[split]


def test_dimreduce():
    global centroids_dict, xyz_dict
    xyz_dict = dim_reduce_clusters(centroids_dict, n_neighbors=5, min_dist=0.25)
    assert xyz_dict.keys() == SPLITS.keys()
    for split, split_xyz in xyz_dict.items():
        assert isinstance(split_xyz, pd.DataFrame)
        assert list(split_xyz.index) == list(range(NCLUSTERS))
        assert tuple(split_xyz.columns) == ('x', 'y', 'z')
