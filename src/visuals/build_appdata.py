#!/usr/bin/env python3

""" Preprocess and build a single file for the data to be used in Dash app. """

import pickle
import sys

import numpy as np
import pandas as pd


def main(dimreduced_file, clusters_file, percentiles_file, out_file):

    with open(dimreduced_file, 'rb') as f:
        xyz = pickle.load(f)
    with open(clusters_file, 'rb') as f:
        clusters = pickle.load(f)
    with open(percentiles_file, 'rb') as f:
        percentiles = pickle.load(f)
    with open('../../reference/skills.csv', 'r') as f:
        skills = f.read().strip().split('\n')

    data = {}
    for split, xyz_data in xyz.items():
        num_clusters = len(xyz_data)

        if split == 'all':
            skills_in_split = skills
        elif split == 'cb':
            skills_in_split = skills[:8]
        elif split == 'noncb':
            skills_in_split = [skills[0]] + skills[8:]

        perc_cols = []
        perc_data = np.zeros((num_clusters, 5 * len(skills_in_split)), dtype='int')
        for i, p in enumerate((0, 25, 50, 75, 100)):
            for j, skill in enumerate(skills_in_split):

                col_i = i * len(split_skills) + j
                perc_cols.append("{}_{}".format(skill, p))
                perc_data[:, col_i] = np.floor(percentiles[split][p][:, j])

        perc_df = pd.DataFrame(perc_data, columns=perc_columns)
        xyz_df = pd.DataFrame(xyz_data, columns=columns)

        data[split]['xyz'] = xyz_df
        data[split]['percentiles'] = perc_df
        data[split]['cluster_sizes'] = clusters[split]['cluster_sizes']
        data[split]['axis_limits'] = {
            'x': (np.min(xyz_df['x']), np.max(xyz_df['x'])),
            'y': (np.min(xyz_df['y']), np.max(xyz_df['y'])),
            'z': (np.min(xyz_df['z']), np.max(xyz_df['z']))
        }

    with open(out_file, 'wb') as f:
        pickle.dump(data, f)


if __name__ == '__main__':
    main(*sys.argv[1:])
