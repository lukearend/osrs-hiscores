import sys

import numpy as np

from src import load_skill_splits, load_stats_data, load_centroid_data
from src.models import cluster_L2


def main(stats_file, centroids_file, out_file):
    splits = load_skill_splits()
    centroids = load_centroid_data(centroids_file)
    _, stats, data = load_stats_data(stats_file)
    data = np.delete(data, stats.index("total"), axis=1)  # drop total levels

    results = {}
    for splitname, split in splits.items():
        player_vectors = data[:, split.skill_inds]
        clusterids = cluster_L2(player_vectors, centroids=centroids)
        clusterids = np.array(clusterids).astype('int')
        results[splitname] = clusterids

    print(clusterids)


if __name__ == "__main__":
    main(*sys.argv[1:])
