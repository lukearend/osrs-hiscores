""" Cluster players according to account similarity. """

import argparse
from typing import Tuple, List

import pandas as pd


def main(players_df: pd.DataFrame, k: int, use_skills: List[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cluster players according to account similarity. """)
    parser.add_argument('-i', '--in-file', type=str, help="load player stats from this file")
    parser.add_argument('--out-clusterids', type=str, help="write cluster IDs to this file")
    parser.add_argument('--out-centroids', type=str, help="write cluster centroids to this file")
    parser.add_argument('-k', '--nclusters', required=True, help="number of clusters")
    parser.add_argument('-v', '--verbose', action='store_true', help="if set, output progress during training")
    args = parser.parse_args()

    # todo: read stats_file
    # todo: read split file and iterate through splits
    # todo: dump centroids_file
    # todo: dump clusterids_file
