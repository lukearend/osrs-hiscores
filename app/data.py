from dataclasses import dataclass
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


def compute_scatterplot_data(splitdata: SplitData, colorstat: str, levelrange: Tuple,
                             n_neighbors: int, min_dist: float) -> pd.DataFrame:
    """
    Assemble the pandas.DataFrame scatterplot is based on.

    :param splitdata: data for the split being displayed
    :param colorstat: skill to use for plot color and level range
    :param levelrange: show clusters whose mean in the given skill is inside this range
    :param n_neighbors: n_neighbors UMAP parameter
    :param min_dist: min_dist UMAP parameter
    :return: pandas.DataFrame with the following columns:
             'x', 'y', 'z', 'id', 'size', 'uniqueness', 'level'
    """
    # When level selector is used, we display only those clusters whose median
    # in the chosen skill is within the selected range.
    statnames = ['total'] + splitdata.skills
    statcol = statnames.index(colorstat)
    stat_median = splitdata.clusterdata.quartiles[:, 2, statcol]  # median level in stat to color by

    lmin, lmax = levelrange
    show_inds = np.where(np.logical_and(lmin <= stat_median, stat_median <= lmax))[0]
    xyz = splitdata.clusterdata.xyz[n_neighbors][min_dist][show_inds]
    nplayers = splitdata.clusterdata.sizes[show_inds]
    uniqueness = 100 * splitdata.clusterdata.uniqueness[show_inds]

    return pd.DataFrame({
        'x': xyz[:, 0],
        'y': xyz[:, 1],
        'z': xyz[:, 2],
        'id': show_inds,
        'size': nplayers,
        'uniqueness': uniqueness,
        'level': stat_median[show_inds]
    })


def compute_boxplot_data(splitname: str, splitdata: SplitData, clusterid=None) -> Dict[str, NDArray]:
    """
    Compute data to display in the boxplot for a given cluster ID.

    :param splitdata: data for the split being displayed
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

    quartiles = splitdata.clusterdata.quartiles[clusterid]
    quartiles = quartiles[:, 1:]  # drop total level

    q0, q1, q2, q3, q4 = quartiles
    iqr = q3 - q1
    lowerfence = np.maximum(q1 - 1.5 * iqr, q0)
    upperfence = np.minimum(q3 + 1.5 * iqr, q4)

    data = np.array([lowerfence, q1, q2, q3, upperfence])
    data = np.round(data)

    # Change columns of data from canonical ordering to ordering of boxplot ticks.
    reorder_inds = ticklabel_skill_inds(splitname, tuple(splitdata.skills))
    data = data[:, reorder_inds]

    nancols = np.isnan(data[2, :])
    data[:, nancols] = hideval

    quartiles_dict = {}
    for i, q in enumerate(['lowerfence', 'q1', 'median', 'q3', 'upperfence']):
        quartiles_dict[q] = data[i, :]
    return quartiles_dict


@lru_cache()
def ticklabel_skill_inds(splitname: str, skills_in_split: Tuple[str]) -> List[int]:
    """ Build index for reordering skills to match tick labels along box plot x-axis. """
    tick_labels = load_boxplot_layout(splitname).ticklabels
    reorder_inds = [skills_in_split.index(s) for s in tick_labels]
    return reorder_inds


@dataclass
class BoxplotLayout:
    """ Contains layout information for rendering boxplot for a specific split. """
    ticklabels: List[str]
    tickxoffset: float


@lru_cache()
def load_boxplot_layout(split: str) -> BoxplotLayout:
    """
    Load layout information for boxplot for the given split.
    :split: name of the split being displayed
    :return: split-specific object containing layout info for rendering boxplot
      -
      - x offset value for the icons used as tick labels
    """
    ticklabels_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_ticklabels.json'
    with open(ticklabels_file, 'r') as f:
        tick_labels = json.load(f)[split]

    offsets_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_offsets.json'
    with open(offsets_file, 'r') as f:
        x_offset = json.load(f)[split]

    return BoxplotLayout(
        ticklabels=tick_labels,
        tickxoffset=x_offset
    )


@lru_cache()
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
        file = Path(__file__).resolve().parents[1] / 'data' / 'processed' / 'app_data.pkl'
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
