from functools import lru_cache
import json
import pickle
from io import BytesIO
from pathlib import Path

import boto3
import numpy as np
import pandas as pd


def compute_scatterplot_data(app_data, split, skill, level_range, n_neighbors, min_dist):
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
    nplayers = app_data[split]['cluster_sizes'][show_inds]
    uniqueness = 100 * app_data[split]['cluster_uniqueness'][show_inds]
    median_level = app_data[split]['cluster_quartiles'][:, 2, skill_i][show_inds]

    return pd.DataFrame({
        'x': xyz_data[:, 0],
        'y': xyz_data[:, 1],
        'z': xyz_data[:, 2],
        'id': cluster_ids,
        'size': nplayers,
        'uniqueness': uniqueness,
        'level': median_level
    })


def compute_boxplot_data(app_data, boxplot_inds, split, cluster_id=None):
    # Replace nans with -100 so we don't see them on the chart (a bit hacky)
    hide_value = -100
    if cluster_id is None:
        nskills = len(app_data[split]['skills'])
        plot_data = {}
        for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']:
            plot_data[q] = np.full(nskills, hide_value)
        return plot_data

    quartiles = app_data[split]['cluster_quartiles'][cluster_id - 1]
    quartiles = quartiles[:, 1:]  # drop total level

    q0, q1, q2, q3, q4 = quartiles
    iqr = q3 - q1
    lower_fence = np.maximum(q1 - 1.5 * iqr, q0)
    upper_fence = np.minimum(q3 + 1.5 * iqr, q4)

    data = np.array([lower_fence, q1, q2, q3, upper_fence])
    data = np.round(data)
    data = data[:, boxplot_inds[split]]

    nan_inds = np.isnan(data[2, :])
    data[:, nan_inds] = hide_value

    plot_data = {}
    for i, q in enumerate(['lowerfence', 'q1', 'median', 'q3', 'upperfence']):
        plot_data[q] = data[i]
    return plot_data


def get_boxplot_inds(app_data):
    boxplot_skills = load_boxplot_layout()

    # Build index lists for reordering skills from canonical order
    # to order of tick marks along x-axis of box plot.
    boxplot_inds = {}
    for split in app_data.keys():
        split_skills = app_data[split]['skills'][1:]  # exclude total level
        reorder_inds = [split_skills.index(skill) for skill in boxplot_skills[split]]
        boxplot_inds[split] = reorder_inds

    return boxplot_inds


@lru_cache(maxsize=None)
def load_boxplot_layout():
    boxplot_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_ticks.json'
    with open(boxplot_file, 'r') as f:
        return json.load(f)


@lru_cache(maxsize=None)
def load_table_layout():
    layout_file = Path(__file__).resolve().parent / 'assets' / 'table_layout.json'
    with open(layout_file, 'r') as f:
        return json.load(f)


def load_appdata_local():
    file_path = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'app_data.pkl'
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def load_appdata_s3(bucket, obj_key):
    print("loading app data...", end=' ', flush=True)
    f = BytesIO()
    s3 = boto3.client('s3')
    s3.download_fileobj(bucket, obj_key, f)
    f.seek(0)
    app_data = pickle.load(f)
    print("done")
    return app_data
