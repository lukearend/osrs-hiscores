from dataclasses import dataclass
from pathlib import Path


@dataclass
class FilePaths:
    stats: str = Path(__file__).resolve().parent / "data" / "player-stats-10000.csv"
    centroids: str = Path(__file__).resolve().parent / "data" / "cluster-centroids-20.csv"
    clusters: str = Path(__file__).resolve().parent / "data" / "player-clusters-20.csv"
    clusters_xyz: str = Path(__file__).resolve().parent / "data" / "clusters_xyz-20.pkl"
    cluster_analytics: str = Path(__file__).resolve().parent / "data" / "cluster_analytics-20.pkl"
    app_data: str = Path(__file__).resolve().parent / "data" / "app_data-20.pkl"
    kmeans_params: str = Path(__file__).resolve().parent / "kmeans_params-20.json"
    umap_params: str = Path(__file__).resolve().parent / "umap_params-20.json"
