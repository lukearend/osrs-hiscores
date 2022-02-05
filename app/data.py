import json
import pathlib
import pickle

import numpy as np
import pandas as pd


data_file = pathlib.Path(__file__).resolve().parent / 'assets/app_data.pkl'
with open(data_file, 'rb') as f:
    app_data = pickle.load(f)


def compute_scatterplot_data(split, skill, level_range, n_neighbors, min_dist):
    # When level selector is used, we display only those clusters whose
    # interquartile range in the chosen skill overlaps the selected range.
    skill_i = app_data[split]['skills'].index(skill)
    levels_q1 = app_data[split]['cluster_quartiles'][:, 1, skill_i]  # 25th percentile
    levels_q3 = app_data[split]['cluster_quartiles'][:, 3, skill_i]  # 75th percentile

    level_min, level_max = level_range
    show_inds = np.where(np.logical_and(
        levels_q3 >= level_min,
        levels_q1 <= level_max,
        ))[0]

    cluster_ids = show_inds + 1
    xyz_data = app_data[split]['xyz'][n_neighbors][min_dist][show_inds]
    num_players = app_data[split]['cluster_sizes'][show_inds]
    uniqueness = 100 * app_data[split]['cluster_uniqueness'][show_inds]
    median_level = app_data[split]['cluster_quartiles'][:, 2, skill_i][show_inds]

    return pd.DataFrame({
        'x': xyz_data[:, 0],
        'y': xyz_data[:, 1],
        'z': xyz_data[:, 2],
        'id': cluster_ids,
        'size': num_players,
        'uniqueness': uniqueness,
        'level': median_level
    })


# Build index lists for reordering skills from canonical order
# to order of tick marks along x-axis of box plot.
boxplot_file = pathlib.Path(__name__).resolve().parent / 'assets' / 'boxplot_ticks.json'
with open(boxplot_file, 'r') as f:
    boxplot_skills = json.load(f)

boxplot_skill_inds = {}
for split in app_data.keys():
    split_skills = app_data[split]['skills'][1:]  # exclude total level
    reorder_inds = [split_skills.index(skill) for skill in boxplot_skills[split]]
    boxplot_skill_inds[split] = reorder_inds

def compute_boxplot_data(split, cluster_id=None):
    # Replace nans with -100 so we don't see them on the chart (a bit hacky)
    hide_value = -100
    if cluster_id is None:
        num_skills = len(app_data[split]['skills'])
        plot_data = {}
        for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']:
            plot_data[q] = np.full(num_skills, hide_value)
        return plot_data

    quartiles = app_data[split]['cluster_quartiles'][cluster_id - 1]
    quartiles = quartiles[:, 1:]  # drop total level

    q0, q1, q2, q3, q4 = quartiles
    iqr = q3 - q1
    lower_fence = np.maximum(q1 - 1.5 * iqr, q0)
    upper_fence = np.minimum(q3 + 1.5 * iqr, q4)

    data = np.array([lower_fence, q1, q2, q3, upper_fence])
    data = np.round(data)
    data = data[:, boxplot_skill_inds[split]]

    nan_inds = np.isnan(data[2, :])
    data[:, nan_inds] = hide_value

    plot_data = {}
    for i, q in enumerate(['lowerfence', 'q1', 'median', 'q3', 'upperfence']):
        plot_data[q] = data[i]
    return plot_data
