#!/usr/bin/env python3

""" Preprocess and build a single file for the data to be used in Dash app. """

import pathlib
import pickle
import sys

import numpy as np
import pandas as pd


def main(dimreduced_file, clusters_file, percentiles_file, out_file):
    print("building app data...", end=' ', flush=True)

    skills_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/skills.csv'
    with open(skills_file, 'r') as f:
        skills = f.read().strip().split('\n')
    with open(clusters_file, 'rb') as f:
        cluster_data = pickle.load(f)
    with open(percentiles_file, 'rb') as f:
        percentile_data = pickle.load(f)
    with open(dimreduced_file, 'rb') as f:
        xyz_data = pickle.load(f)

    splits = list(xyz_data.keys())
    percentiles = list(percentile_data[splits[0]].keys())

    appdata = {}
    for split in splits:

        if split == 'all':
            skills_in_split = skills
        elif split == 'cb':
            skills_in_split = skills[:8]
        elif split == 'noncb':
            skills_in_split = [skills[0]] + skills[8:]

        num_clusters = cluster_data[split]['num_clusters']
        cluster_stats = np.zeros((num_clusters, len(skills_in_split), len(percentiles)))

        # Transform the percentile data into a data structure that is more
        # efficient for accessing by cluster ID during a callback.

        for cluster_id in range(num_clusters):
            for i, percent in enumerate(percentiles):
                skill_percentiles = percentile_data[split][percent][cluster_id, :]
                cluster_stats[cluster_id, :, i] = skill_percentiles

        appdata[split] = {
            'skills': skills_in_split,
            'xyz': xyz_data[split],
            'cluster_stats': cluster_stats,
            'cluster_sizes': cluster_data[split]['cluster_sizes'],
            'percent_uniqueness': cluster_data[split]['percent_uniqueness'],
            'axis_limits': {
                'x': (np.min(xyz_data[split][:, 0]), np.max(xyz_data[split][:, 0])),
                'y': (np.min(xyz_data[split][:, 1]), np.max(xyz_data[split][:, 1])),
                'z': (np.min(xyz_data[split][:, 2]), np.max(xyz_data[split][:, 2]))
            }
        }

    with open(out_file, 'wb') as f:
        pickle.dump(appdata, f)


if __name__ == '__main__':
    main(*sys.argv[1:])
