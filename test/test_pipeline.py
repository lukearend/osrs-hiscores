from pathlib import Path

from scripts.cluster_players import main as cluster_players
# from scripts.compute_quartiles import main as compute_quartiles
# from scripts.dim_reduce_clusters import main as dim_reduce_clusters
# from scripts.build_app_data import main as build_app_data

from src.analysis.data import import_players_csv


STATS_FILE = Path(__file__).resolve().parent / "data" / "test-data.csv"


if __name__ == '__main__':
    players_df = import_players_csv(STATS_FILE)
