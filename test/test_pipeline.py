import csv
from collections import OrderedDict
from pathlib import Path

import pandas as pd
import xarray as xr

from scripts.cluster_players import main as cluster_players
from scripts.compute_quartiles import main as compute_quartiles
from scripts.dim_reduce_clusters import main as dim_reduce_clusters
from scripts.build_app import build_app_data, build_app_database
from src.analysis.app import PlayerResults, SplitData, connect_mongo, mongo_get_player

from src.analysis.data import import_players_csv, export_players_csv, export_clusterids_csv, export_centroids_csv
from src import osrs_skills

SPLITS = OrderedDict([
    ("first5", ["attack", "defence", "strength", "hitpoints", "ranged"]),
    ("last10", ["smithing", "mining", "herblore", "agility", "thieving",
                "slayer", "farming", "runecraft", "hunter", "construction"])
])
NCLUSTERS_PER_SPLIT = {"first5": 50, "last10": 25}
UMAP_NN_PER_SPLIT = {"first5": 5, "last10": 10}
UMAP_MINDIST_PER_SPLIT = {"first5": 0.25, "last10": 0.10}


global players_df
global clusterids_df, centroids_dict
global quartiles_dict
global xyz_dict


def test_import_csv():
    global players_df
    stats_file = Path(__file__).resolve().parent / "data" / "test-data.csv"
    players_df = import_players_csv(stats_file)
    assert isinstance(players_df, pd.DataFrame)
    assert len(players_df) == 10000
    assert list(players_df.columns) == osrs_skills(include_total=True)


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


def test_buildapp():
    global players_df, clusterids_df, centroids_dict, quartiles_dict, xyz_dict
    app_data = build_app_data(SPLITS, clusterids_df, centroids_dict, quartiles_dict, xyz_dict)
    assert app_data.keys() == SPLITS.keys()
    for split, split_data in app_data.items():
        nclusters = NCLUSTERS_PER_SPLIT[split]
        assert isinstance(split_data, SplitData)
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

    coll = connect_mongo("localhost:27017", 'test')
    coll.drop()
    build_app_database(players_df, clusterids_df, coll)
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

    export_clusterids_csv(clusterids_df, clusterids_file)
    with open(clusterids_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ['player'] + list(SPLITS.keys())
        for nlines, line in enumerate(reader, start=1):
            assert len(line) == len(header)
        assert nlines == 10000

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
