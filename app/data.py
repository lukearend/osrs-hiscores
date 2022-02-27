from functools import lru_cache
import json
import pickle
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

import boto3
import numpy as np
import pandas as pd
from numpy.typing import NDArray

from src.results import AppData, SplitData


def compute_scatterplot_data(splitdata: SplitData, skill: str, levelrange: Tuple,
                             n_neighbors: int, min_dist: float) -> pd.DataFrame:
    """
    Assemble the pandas.DataFrame scatterplot is based on.

    :param splitdata: data for the split being displayed
    :param skill: skill to use for plot color and level range
    :param levelrange: show clusters whose mean in the given skill is inside this range
    :param n_neighbors: n_neighbors UMAP parameter
    :param min_dist: min_dist UMAP parameter
    :return: pandas.DataFrame with the following columns:
             'x', 'y', 'z', 'id', 'size', 'uniqueness', 'level'
    """
    # When level selector is used, we display only those clusters whose
    # interquartile range in the chosen skill overlaps the selected range.
    skill_i = splitdata.skills.index(skill)
    q1 = splitdata.clusterdata.quartiles[:, 1, skill_i]  # 25th percentile
    q3 = splitdata.clusterdata.quartiles[:, 1, skill_i]  # 75th percentile

    lmin, lmax = levelrange
    show_inds = np.where(np.logical_and(q1 >= lmin, q3 <= lmax))[0]
    cluster_ids = show_inds + 1
    xyz = splitdata.clusterdata.xyz[n_neighbors][min_dist][show_inds]
    nplayers = splitdata.clusterdata.sizes[show_inds]
    uniqueness = 100 * splitdata.clusterdata.uniqueness[show_inds]
    median_level = splitdata.clusterdata.quartiles[:, 2, skill_i][show_inds]

    return pd.DataFrame({
        'x': xyz[:, 0],
        'y': xyz[:, 1],
        'z': xyz[:, 2],
        'id': cluster_ids,
        'size': nplayers,
        'uniqueness': uniqueness,
        'level': median_level
    })


def compute_boxplot_data(splitdata: SplitData, boxplot_inds: List, clusterid=None) -> Dict[str, NDArray]:
    """
    Compute data to display in the boxplot for a given cluster ID.

    :param splitdata: data for the split being displayed
    :param boxplot_inds: list of indexes which reorders split skills into boxplot tick labels
    :param clusterid: plot data for this cluster (otherwise generate data for empty plot)
    :return: dictionary where keys are boxplot quartile names and values are 1D arrays
             giving the quartile value in each skill of the current split
    """
    hideval = -100  # replace nans with an off-plot value to hide them
    if clusterid is None:
        nskills = len(splitdata.skills)
        plot_data = {}
        for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']:
            plot_data[q] = np.full(nskills, hideval)
        return plot_data

    quartiles = splitdata.clusterdata.quartiles[clusterid - 1]
    quartiles = quartiles[:, 1:]  # drop total level

    q0, q1, q2, q3, q4 = quartiles
    iqr = q3 - q1
    lowerfence = np.maximum(q1 - 1.5 * iqr, q0)
    upperfence = np.minimum(q3 + 1.5 * iqr, q4)

    data = np.array([lowerfence, q1, q2, q3, upperfence])
    data = np.round(data)
    data = data[:, boxplot_inds]

    nanlocs = np.isnan(data[2, :])
    data[:, nanlocs] = hideval

    quartiles_dict = {}
    for i, q in enumerate(['lowerfence', 'q1', 'median', 'q3', 'upperfence']):
        quartiles_dict[q] = data[i]
    return quartiles_dict


# TODO: code smell, turn this into a more direct reordering of the skills -> ticklabels, and lru_cache it
def get_boxplot_inds(appdata: AppData) -> Dict[str, List[int]]:
    """ Build index for reordering skills to match tick labels along box plot x-axis. """
    skillinds_per_split = {}
    for splitname, split in appdata.splitdata.items():
        boxplot_skills = load_boxplot_layout(splitname)[0]
        reorder_inds = [split.skills.index(s) for s in boxplot_skills]
        skillinds_per_split[splitname] = reorder_inds
    return skillinds_per_split


@lru_cache(maxsize=None)
def load_boxplot_layout(split: str) -> Tuple[Dict[str, List[str]], Dict[str, float]]:
    """
    Load layout information for boxplot for the given split.
    :split: name of the split being displayed
    :return:
      - dictionary mapping split names to the list of skills to use as tick labels
      - dictionary mapping split names to x offsets for the icons used as tick labels
    """
    ticklabels_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_ticklabels.json'
    with open(ticklabels_file, 'r') as f:
        ticklabels = json.load(f)[split]

    offsets_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_offsets.json'
    with open(offsets_file, 'r') as f:
        x_offsets = json.load(f)[split]

    return ticklabels, x_offsets


@lru_cache(maxsize=None)
def load_table_layout() -> List[List[str]]:
    """
    Load layout for the skills to be displayed in skill tables.
    :return: list of lists where each inner list gives the skills in a table row
    """
    layout_file = Path(__file__).resolve().parent / 'assets' / 'table_layout.json'
    with open(layout_file, 'r') as f:
        return json.load(f)


def load_appdata_local(file: str = None) -> AppData:
    """
    Load the object containing all data needed to drive this Dash application.
    :param file: load from this local file (optional, otherwise uses default location)
    :return: application data object built by project source code
    """
    if not file:
        file = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'app_data.pkl'
    with open(file, 'rb') as f:
        app_data: AppData = pickle.load(f)
        return app_data


def load_appdata_s3(bucket: str, obj_key: str) -> AppData:
    """
    Load the object containing all data needed to drive this Dash application.
    :bucket: AWS S3 bucket to download app data from
    :obj_key: key to object to download within bucket
    :return: application data object built by project source code
    """
    print("downloading app data...", end=' ', flush=True)
    f = BytesIO()
    s3 = boto3.client('s3')
    s3.download_fileobj(bucket, obj_key, f)
    print("done")
    f.seek(0)
    app_data: AppData = pickle.load(f)
    return app_data
