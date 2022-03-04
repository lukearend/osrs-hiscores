""" Assign OSRS accounts into clusters based on distance from each
    other in 23D space. Each account is represented as a length-23
    vector of the player's levels in each skill. The distance between
    two accounts is then measured as the sum of squared stat-by-stat
    differences. This is much like taking the Euclidean distance
    between points in 3D space, except the points live in a 23-
    dimensional space instead.

    For k = {"all": 4000, "cb": 2000, "noncb": 2000}, this script
    runs in about 4 hours on a 2021 M1 Mac.
"""
import argparse
from typing import List, Dict

import numpy as np
from codetiming import Timer
from numpy.typing import NDArray

from src.common import DataSplit, skill_splits, load_stats_data, split_dataset
from src.models import kmeans_params, fit_kmeans


def write_results(splits: List[DataSplit], all_skills: List[str], centroids: Dict[str, NDArray], out_file: str):
    print("writing cluster centroids to CSV...")
    with open(out_file, 'w') as f:
        f.write(f"split,clusterid,{','.join(s for s in all_skills)}\n")

        for split in splits:
            # Each split contains a different subset of skills. We need
            # to map the skill columns in the centroid results for each
            # split to their indexes in the original list of all stats.
            # Build a map to use for these lookups in the inner loop.
            ind_map = {}
            for i, s in enumerate(split.skills):
                try:
                    ind_map[i] = split.skills.index(s)
                except ValueError:
                    pass

            for clusterid, centroid in enumerate(centroids[split.name]):
                line = []
                for i in range(len(split.skills)):
                    stat_ind = ind_map.get(i, None)
                    stat_value = centroid[stat_ind] if stat_ind is not None else ''
                    line.append(stat_value)

                centroid_csv = ','.join(str(v) for v in line)
                line = f"{split.name},{clusterid},{centroid_csv}\n"
                f.write(line)


@Timer(text="done fitting clusters (total time {:.2f} sec)")
def main(stats_file: str, out_file: str, params_file: str = None, verbose: bool = True):
    _, statnames, data = load_stats_data(stats_file, include_total=False)

    centroids_per_split = {}
    splits = skill_splits()
    params = kmeans_params(params_file)
    for split in splits:
        player_vectors = split_dataset(data, split)

        # Player weight is proportional to the number of ranked skills.
        weights = np.sum(player_vectors != -1, axis=1) / split.nskills

        # Replace missing data, i.e. unranked stats, with 1s. This is
        # a reasonable substitution for clustering purposes since an
        # unranked stat is known to be relatively low.
        player_vectors[player_vectors == -1] = 1

        k = params[split.name]
        centroids = fit_kmeans(player_vectors, k=k, w=weights, verbose=verbose)

        # Sort clusters by total level descending.
        total_levels = np.sum(centroids, axis=1)
        sort_inds = np.argsort(total_levels)[::-1]
        centroids = centroids[sort_inds]

        centroids_per_split[split.name] = centroids

    all_skills = [s.skills for s in splits if s.name == "all"][0]
    write_results(splits, all_skills, centroids_per_split, out_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fit cluster centroids on player stats data.""")
    parser.add_argument('statsfile', type=str, help="load player stats from this CSV file")
    parser.add_argument('outfile', type=str, help="write cluster centroids to this file")
    parser.add_argument('paramsfile', type=str, required=False,
                        help="load k-means parameters from this file (if not provided, uses default location)")
    parser.add_argument('-v', '--verbose', type=str, action='store_true',
                        help="whether to output progress during training")
    args = parser.parse_args()
    main(args.statsfile, args.outfile, args.paramsfile, args.verbose)
