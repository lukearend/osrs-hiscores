from dataclasses import dataclass
from pathlib import Path
testdir = Path(__file__).resolve().parent


def load_testdata():
    pass


@dataclass
class FilePaths:
    usernames_raw: str = testdir / "data" / "usernames-raw.csv"
    usernames: str = testdir / "data" / "usernames.csv"
    stats_raw: str = testdir / "data" / "stats-raw.csv"
    stats: str = testdir / "data" / "player-stats.csv"
    centroids: str = testdir / "data" / "cluster-centroids.csv"
    clusters: str = testdir / "data" / "player-clusters.csv"
    clusters_xyz: str = testdir / "data" / "clusters_xyz.pkl"
    cluster_analytics: str = testdir / "data" / "cluster_analytics.pkl"
    app_data: str = testdir / "data" / "app_data.pkl"
    kmeans_params: str = testdir / "kmeans_params.json"
    umap_params: str = testdir / "umap_params.json"
