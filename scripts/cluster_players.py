import argparse
import csv
from typing import Dict

from codetiming import Timer
from numpy.typing import NDArray

from src import load_splits, load_stats_data, load_centroid_data
from src.data import split_dataset
from src.models import cluster_l2


@Timer(text="done clustering players (total time {:.2f} sec)")
def main(player_data: NDArray, centroids_per_split: NDArray) -> Dict[str, NDArray]:
    clusterids_per_split = {}
    for splitname, centroids in centroids_per_split.items():
        player_vectors = split_dataset(player_data, splitname)

        print(f"clustering split '{splitname}'...", end=' ', flush=True)
        with Timer("done ({:.2f} sec)"):
            clusterids = cluster_l2(player_vectors, centroids=centroids_per_split[splitname])
        clusterids_per_split[splitname] = clusterids

    return clusterids_per_split


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fit cluster centroids on player stats data.""")
    parser.add_argument('statsfile', type=str, help="load player stats from this CSV file")
    parser.add_argument('centroidsfile', type=str, help="load cluster centroids from this CSV file")
    parser.add_argument('outfile', type=str, help="write cluster IDs to this file")
    args = parser.parse_args()

    splits = load_splits()
    centroids_per_split = load_centroid_data(args.centroidsfile)
    usernames, _, player_data = load_stats_data(args.statsfile, include_total=False)
    clusterids_per_split = main(player_data, centroids_per_split, args.outfile)

    print("writing player clusters to CSV...")
    lines = []
    splitnames = [split.name for split in splits]
    for i, username in enumerate(usernames):
        player_clusterids = [clusterids_per_split[s][i] for s in splitnames]
        line = [username, *player_clusterids]
        lines.append(line)

    with open(args.outfile, 'w') as f:
        header = ["username", *splitnames]
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(lines)
