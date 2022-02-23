""" Assign OSRS accounts into clusters based on distance from each
    other in 23D space. Each account is represented as a length-23
    vector of the player's levels in each skill. The distance between
    two accounts is then measured as the sum of squared stat-by-stat
    differences. This is just like taking the Euclidean distance
    between points in 3D space, except the points live in a 23-
    dimensional space instead.
"""

import sys

import numpy as np

from src import load_kmeans_params, load_skill_splits, load_stats_data
from src.models import fit_kmeans


def main(stats_file, out_file):
    params = load_kmeans_params()
    splits = load_skill_splits()
    _, stats, data = load_stats_data(stats_file)
    data = np.delete(data, stats.index("total"), axis=1)  # drop total level column

    centroids = {}
    for split in splits:
        player_vectors = data[:, split.skill_inds].copy()

        # Player weight is proportional to the number of ranked skills.
        weights = np.sum(player_vectors != -1, axis=1) / split.nskills

        # Replace missing data, i.e. unranked stats, with 1s. This is
        # a reasonable substitution for clustering purposes since an
        # unranked stat is known to be relatively low.
        player_vectors[player_vectors == -1] = 1

        k = params[split.name]
        centroids[split.name] = fit_kmeans(player_vectors, k=k, w=weights)

    print("writing cluster centroids to CSV...", end=' ', flush=True)
    with open(out_file, 'w') as f:
        skills = stats[1:]
        f.write(f"split,clusterid,{','.join(s for s in skills)}\n")

        for split in splits:
            # Each split contains a different subset of skills. We need
            # to map the skill columns in the centroid results for each
            # split to their indexes in the original list of all stats.
            # Build a map to use for these lookups in the inner loop.
            ind_map = {}
            for i, s in enumerate(skills):
                try:
                    ind_map[i] = split.skills.index(s)
                except ValueError:
                    pass

            for clusterid, centroid in enumerate(centroids[split.name]):
                line = []
                for i in range(len(skills)):
                    stat_ind = ind_map.get(i, None)
                    stat_value = centroid[stat_ind] if stat_ind is not None else ''
                    line.append(stat_value)

                centroid_csv = ','.join(str(v) for v in line)
                line = f"{split.name},{i},{centroid_csv}\n"
                f.write(line)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
