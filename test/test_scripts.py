import csv
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from scripts.build_app_data import main as build_app_data
from scripts.build_app_db import main as build_app_database
from scripts.cluster_players import main as cluster_players
from scripts.compute_quartiles import main as compute_quartiles
from scripts.dim_reduce_clusters import main as dim_reduce_clusters
from src.common import osrs_skills, connect_mongo
from src.data.db import mongo_get_player
from src.data.io import export_players_csv, export_clusterids_csv, export_centroids_csv, import_players_csv, \
    import_clusterids_csv, import_centroids_csv
from src.data.types import PlayerResults, SplitResults


SPLITS = OrderedDict([
    ("first5", ["attack", "defence", "strength", "hitpoints", "ranged"]),
    ("last10", ["smithing", "mining", "herblore", "agility", "thieving",
                "slayer", "farming", "runecraft", "hunter", "construction"])
])
NCLUSTERS_PER_SPLIT = {"first5": 40, "last10": 25}
UMAP_NN_PER_SPLIT = {"first5": 5, "last10": 10}
UMAP_MINDIST_PER_SPLIT = {"first5": 0.25, "last10": 0.10}


global players_df
global clusterids_df, centroids_dict
global quartiles_dict
global xyz_dict


def test_setup():
    global players_df
    stats_file = Path(__file__).resolve().parent / "data" / "test-data.csv"
    players_df = import_players_csv(stats_file)


def test_cluster():
    global players_df, clusterids_df, centroids_dict
    clusterids_df, centroids_dict = cluster_players(
        players_df, k_per_split=NCLUSTERS_PER_SPLIT, splits=SPLITS, verbose=False)
    assert isinstance(clusterids_df, pd.DataFrame)
    assert len(clusterids_df) == len(players_df)
    assert tuple(clusterids_df.columns) == tuple(SPLITS.keys())
    for split, skills_in_split in SPLITS.items():
        split_centroids = centroids_dict[split]
        assert isinstance(split_centroids, pd.DataFrame)
        assert list(split_centroids.index) == list(range(NCLUSTERS_PER_SPLIT[split]))
        assert list(split_centroids.columns) == skills_in_split


def test_quartiles():
    global players_df, clusterids_df, quartiles_dict
    quartiles_dict = compute_quartiles(players_df, clusterids_df, SPLITS)
    assert quartiles_dict.keys() == SPLITS.keys()
    for split, split_quartiles in quartiles_dict.items():
        assert isinstance(split_quartiles, xr.DataArray)
        assert list(split_quartiles.dims) == ["percentile", "clusterid", "skill"]
        assert list(split_quartiles.coords["percentile"]) == [0, 25, 50, 75, 100]
        assert list(split_quartiles.coords["clusterid"]) == list(range(NCLUSTERS_PER_SPLIT[split]))
        assert list(split_quartiles.coords["skill"]) == ['total'] + SPLITS[split]


def test_dimreduce():
    global centroids_dict, xyz_dict
    xyz_dict = dim_reduce_clusters(centroids_dict, n_neighbors=UMAP_NN_PER_SPLIT, min_dist=UMAP_MINDIST_PER_SPLIT)
    assert xyz_dict.keys() == SPLITS.keys()
    for split, split_xyz in xyz_dict.items():
        assert isinstance(split_xyz, pd.DataFrame)
        assert list(split_xyz.index) == list(range(NCLUSTERS_PER_SPLIT[split]))
        assert tuple(split_xyz.columns) == ('x', 'y', 'z')


def test_appdata():
    global clusterids_df, centroids_dict, quartiles_dict, xyz_dict
    app_data = build_app_data(SPLITS, clusterids_df, centroids_dict, quartiles_dict, xyz_dict)
    assert app_data.keys() == SPLITS.keys()
    for split, split_data in app_data.items():
        nclusters = NCLUSTERS_PER_SPLIT[split]
        assert isinstance(split_data, SplitResults)
        assert split_data.skills == SPLITS[split]
        assert isinstance(split_data.cluster_quartiles, xr.DataArray)
        assert isinstance(split_data.cluster_centroids, pd.DataFrame)
        assert isinstance(split_data.cluster_xyz, pd.DataFrame)
        assert split_data.cluster_quartiles.shape == (5, nclusters, len(split_data.skills) + 1)
        assert split_data.cluster_centroids.shape == (nclusters, len(split_data.skills))
        assert split_data.cluster_xyz.shape == (nclusters, 3)
        assert len(split_data.cluster_sizes) == nclusters
        assert len(split_data.cluster_uniqueness) == nclusters
        assert tuple(split_data.xyz_axlims.keys()) == ('x', 'y', 'z')
        for axlimits in split_data.xyz_axlims.values():
            assert axlimits[0] <= axlimits[1]

def test_appdb():
    global players_df, clusterids_df
    coll = connect_mongo("localhost:27017", 'test')
    coll.drop()
    build_app_database(players_df, clusterids_df, coll, batch_size=789)
    assert coll.count_documents({}) == len(players_df)

    for uname in [d['username'] for d in coll.find({}, limit=5)]:
        player = mongo_get_player(coll, uname)
        assert isinstance(player, PlayerResults)
        assert len(player.stats) == len(osrs_skills(include_total=True))
        for split, clusterid in player.clusterids.items():
            assert split in SPLITS
            assert isinstance(clusterid, int)

    coll.drop()


def test_export():
    global players_df, clusterids_df, centroids_dict
    data_dir = Path(__file__).resolve().parent / "data"
    stats_file = data_dir / "player-stats.csv"
    clusterids_file = data_dir / "player-clusterids.csv"
    centroids_file = data_dir / "cluster-centroids.csv"

    export_players_csv(players_df, stats_file)
    with open(stats_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ['username', 'rank'] + osrs_skills(include_total=True)
        for nlines, line in enumerate(reader, start=1):
            assert len(line) == len(header)
        assert nlines == 10000

    assert import_players_csv(stats_file).equals(players_df)

    export_clusterids_csv(clusterids_df, clusterids_file)
    with open(clusterids_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ['player'] + list(SPLITS.keys())
        for nlines, line in enumerate(reader, start=1):
            assert len(line) == len(header)
        assert nlines == 10000

    assert import_clusterids_csv(clusterids_file).equals(clusterids_df)

    export_centroids_csv(centroids_dict, centroids_file)
    with open(centroids_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ['split', 'clusterid'] + osrs_skills(include_total=False)
        nlines = 0
        for split in SPLITS.keys():
            nclusters = NCLUSTERS_PER_SPLIT[split]
            for i in range(nclusters):
                line = next(reader)
                assert len(line) == len(header)
                assert line[0] == split
                assert int(line[1]) == i
                skill_vals = [v for v in line[2:] if v]  # drop empty columns for skills not in this split
                assert len(skill_vals) == len(SPLITS[split])
                nlines += 1
        assert nlines == sum(NCLUSTERS_PER_SPLIT.values())

    for split, centroids_df in import_centroids_csv(centroids_file).items():
        diff = abs(centroids_dict[split] - centroids_df)
        assert np.all(diff < 5e-6)
