""" Cluster players according to account similarity. """

import argparse
from typing import Tuple, List

import pandas as pd


def main(players_df: pd.DataFrame, k: int, use_skills: List[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # Player weight is proportional to the number of ranked skills.
    weights = np.sum(player_vectors != -1, axis=1) / player_vectors.shape[1]

    # Replace missing data, i.e. unranked stats, with 1s. This is
    # a reasonable substitution for clustering purposes since an
    # unranked stat is known to be relatively low.
    player_vectors[player_vectors == -1] = 1

    # Sort clusters by total level descending.
    total_levels = np.sum(centroids, axis=1)
    sort_inds = np.argsort(total_levels)[::-1]
    centroids = centroids[sort_inds]


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
