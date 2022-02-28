import csv
import time
import sys

from src.common import skill_splits, load_stats_data, load_centroid_data, split_dataset
from src.models import cluster_l2


def main(stats_file: str, centroids_file: str, out_file: str):
    centroids = load_centroid_data(centroids_file)
    usernames, _, data = load_stats_data(stats_file, include_total=False)

    splits = skill_splits()
    clusterids_per_split = {}
    for split in splits:
        player_vectors = split_dataset(data, split)

        print(f"clustering split '{split.name}'...", end=' ', flush=True)
        t0 = time.time()
        clusterids = cluster_l2(player_vectors, centroids=centroids[split.name])
        print(f"done ({time.time() - t0:.2f} sec)")

        clusterids_per_split[split.name] = clusterids

    print("writing player clusters to CSV...")
    lines = []
    splitnames = [split.name for split in splits]
    for i, username in enumerate(usernames):
        player_clusterids = [clusterids_per_split[s][i] for s in splitnames]
        line = [username, *player_clusterids]
        lines.append(line)

    with open(out_file, 'w') as f:
        header = ["username", *splitnames]
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(lines)


if __name__ == "__main__":
    main(*sys.argv[1:])
