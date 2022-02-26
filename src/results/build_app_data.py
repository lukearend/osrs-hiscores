#!/usr/bin/env python3

""" Preprocess and build a single file for the data to be used in Dash app. """
import pathlib
import pickle
import sys

import numpy as np


def main(cluster_analytics_file, centroids_file, dim_reduced_file, out_file):
    print("building app data...", end=' ', flush=True)

    skills_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/osrs_skills.csv'
    with open(skills_file, 'r') as f:
        skills = f.read().strip().split('\n')
    with open(cluster_analytics_file, 'rb') as f:
        cluster_data = pickle.load(f)
    with open(dim_reduced_file, 'rb') as f:
        xyz_data = pickle.load(f)

    data_splits = list(xyz_data.keys())
    app_data = {}
    for split in data_splits:
        if split == 'cb':
            skills_in_split = skills[:8]
        elif split == 'noncb':
            skills_in_split = [skills[0]] + skills[8:]
        else:
            skills_in_split = skills

        axis_limits = {}
        for n_neighbors, nn_dict in xyz_data[split].items():
            axis_limits[n_neighbors] = {}
            for min_dist, md_dict in nn_dict.items():
                xyz = xyz_data[split][n_neighbors][min_dist]
                axis_limits[n_neighbors][min_dist] = {
                    'x': (np.min(xyz[:, 0]), np.max(xyz[:, 0])),
                    'y': (np.min(xyz[:, 1]), np.max(xyz[:, 1])),
                    'z': (np.min(xyz[:, 2]), np.max(xyz[:, 2]))
                }

        app_data[split] = {
            'skills': skills_in_split,
            'xyz': xyz_data[split],
            'cluster_quartiles': cluster_data['cluster_quartiles'][split],
            'cluster_sizes': cluster_data['cluster_sizes'][split],
            'cluster_uniqueness': cluster_data['cluster_uniqueness'][split],
            'axis_limits': axis_limits
        }

    with open(out_file, 'wb') as f:
        pickle.dump(app_data, f)
    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
