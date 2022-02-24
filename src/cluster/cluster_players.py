import csv
import time
import sys

import numpy as np

from src import load_skill_splits, load_stats_data, load_centroid_data
from src.models import cluster_L2


def main(stats_file, centroids_file, out_file):
    splits = load_skill_splits()
    centroids = load_centroid_data(centroids_file)
    usernames, stats, data = load_stats_data(stats_file)
    data = np.delete(data, stats.index("total"), axis=1)  # drop total levels

    clusterids_per_split = {}
    for split in splits:
        player_vectors = data[:, split.skill_inds]
        player_vectors = player_vectors.copy()  # copy to make C-contiguous array

        print(f"clustering split '{split.name}'...", end=' ', flush=True)
        t0 = time.time()
        clusterids = cluster_L2(player_vectors, centroids=centroids[split.name])
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
