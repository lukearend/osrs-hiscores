#!/usr/bin/env python3

""" Preprocess and build a single file for the data to be used in Dash app. """

import pathlib
import pickle
import sys

import numpy as np
import pandas as pd


def main(cluster_analytics_file, dim_reduced_file, out_file):
    print("building app data...", end=' ', flush=True)

    skills_file = pathlib.Path(__file__).resolve().parents[2] / 'reference/osrs_skills.csv'
    with open(skills_file, 'r') as f:
        skills = f.read().strip().split('\n')
    with open(cluster_analytics_file, 'rb') as f:
        cluster_data = pickle.load(f)
    with open(dim_reduced_file, 'rb') as f:
        xyz_data = pickle.load(f)

    splits = list(xyz_data.keys())

    app_data = {}
    for split in splits:
        if split == 'all':
            skills_in_split = skills
        elif split == 'cb':
            skills_in_split = skills[:8]
        elif split == 'noncb':
            skills_in_split = [skills[0]] + skills[8:]

        app_data[split] = {
            'skills': skills_in_split,
            'xyz': xyz_data[split],
            'cluster_stats': cluster_data['cluster_quartiles'][split],
            'cluster_sizes': cluster_data['cluster_sizes'][split],
            'percent_uniqueness': cluster_data['cluster_uniqueness'][split],
            # TODO:
            # 'axis_limits': {
            #     'x': (np.min(xyz_data[split][:, 0]), np.max(xyz_data[split][:, 0])),
            #     'y': (np.min(xyz_data[split][:, 1]), np.max(xyz_data[split][:, 1])),
            #     'z': (np.min(xyz_data[split][:, 2]), np.max(xyz_data[split][:, 2]))
            # }
        }

    with open(out_file, 'wb') as f:
        pickle.dump(app_data, f)

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
