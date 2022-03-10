from functools import cache
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from app import load_boxplot_layout
from src.results import SplitData


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


@cache
def ticklabel_skill_inds(splitname: str, skills_in_split: Tuple[str]) -> List[int]:
    """ Build index for reordering skills to match tick labels along box plot x-axis. """
    tick_labels = load_boxplot_layout(splitname).ticklabels
    reorder_inds = [skills_in_split.index(s) for s in tick_labels]
    return reorder_inds
