import argparse
from typing import List, Dict

import numpy as np
from codetiming import Timer
from numpy.typing import NDArray

from src import DatasetSplit, load_stats_data, load_splits
from src.analytics.data import split_dataset
from src.models import load_kmeans_params, fit_kmeans


def write_results(header_skills: List[str], splits: List[DatasetSplit],
                  centroids_per_split: Dict[str, NDArray], out_file: str):
    print("writing cluster centroids to CSV...")
    with open(out_file, 'w') as f:
        f.write(f"split,clusterid,{','.join(s for s in header_skills)}\n")
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

            for clusterid, centroid in enumerate(centroids_per_split[split.name]):
                line = []
                for i in range(len(split.skills)):
                    stat_ind = ind_map.get(i, None)
                    stat_value = centroid[stat_ind] if stat_ind is not None else ''
                    line.append(stat_value)

                centroid_csv = ','.join(str(v) for v in line)
                line = f"{split.name},{clusterid},{centroid_csv}\n"
                f.write(line)


def main(player_skills_data: NDArray, k_per_split: Dict[str, int], verbose: bool = True) -> Dict[str, NDArray]:
    """
    Fit clusters for OSRS account data for each split of the dataset.

    :param player_skills_data: 2D array where each row gives a player's level in each stat
    :param k_per_split: k parameter to use for running k-means on each split
    :param verbose: whether to output progress during model fitting
    :return: dictionary mapping split names to cluster centroids for each split
    """
    centroids_per_split = {}
    for splitname, k in k_per_split:
        player_vectors = split_dataset(player_skills_data, splitname)

        # Player weight is proportional to the number of ranked skills.
        weights = np.sum(player_vectors != -1, axis=1) / player_vectors.shape[1]

        # Replace missing data, i.e. unranked stats, with 1s. This is
        # a reasonable substitution for clustering purposes since an
        # unranked stat is known to be relatively low.
        player_vectors[player_vectors == -1] = 1

        centroids = fit_kmeans(player_vectors, k=k, w=weights, verbose=verbose)

        # Sort clusters by total level descending.
        total_levels = np.sum(centroids, axis=1)
        sort_inds = np.argsort(total_levels)[::-1]
        centroids = centroids[sort_inds]

        centroids_per_split[splitname] = centroids

    return centroids_per_split


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fit cluster centroids on player stats data.""")
    parser.add_argument('statsfile', type=str, help="load player stats from this CSV file")
    parser.add_argument('outfile', type=str, help="write cluster centroids to this file")
    parser.add_argument('-p', '--params', type=str, required=False,
                        help="load k-means parameters from this file (if not provided, uses default location)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="if set, will output progress during training")
    args = parser.parse_args()

    _, statnames, skilldata = load_stats_data(args.statsfile, include_total=False)
    splits = load_splits()
    k_per_split = load_kmeans_params(file=args.params)

    with Timer(text="done fitting clusters (total time {:.2f} sec)"):
        centroids_per_split = main(skilldata, k_per_split, verbose=args.verbose)

    write_results(statnames, splits, centroids_per_split, args.outfile)
