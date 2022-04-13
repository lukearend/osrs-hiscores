from typing import Dict, Tuple

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from app import ticklabel_skill_inds
from src.analysis.app import SplitData


def compute_scatterplot_data(split_data: SplitData, color_by_skill: str, color_axis_range: Tuple) -> pd.DataFrame:

    # Display only those clusters whose median in the chosen skill is within the selected range.
    skill_names = ['total'] + split_data.skills
    color_col = skill_names.index(color_by_skill)
    stat_median = split_data.cluster_quartiles[2, :, color_col].to_numpy()

    cmin, cmax = color_axis_range
    within_range = np.logical_and(cmin < stat_median, stat_median <= cmax)
    show_inds = np.where(within_range)[0].astype('int')
    xyz = split_data.cluster_xyz.iloc[show_inds, :]
    return pd.DataFrame({
        'x': xyz['x'],
        'y': xyz['y'],
        'z': xyz['z'],
        'id': show_inds,
        'size': split_data.cluster_sizes[show_inds],
        'uniqueness': 100 * split_data.cluster_uniqueness[show_inds],
        'level': stat_median[show_inds]
    })


def compute_boxplot_data(split: str, split_data: SplitData, clusterid=None) -> Dict[str, NDArray]:

    hide_val = -100  # replace nans with an off-plot value to hide them
    if clusterid is None:
        plot_data = {}
        for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']:
            plot_data[q] = np.full(len(split_data.skills), hide_val)
        return plot_data

    quartiles = split_data.cluster_quartiles[:, clusterid, :]
    quartiles = quartiles.where(quartiles.skill != 'total', drop=True)

    q0, q1, q2, q3, q4 = quartiles
    iqr = q3 - q1
    lowerfence = np.maximum(q1 - 1.5 * iqr, q0)
    upperfence = np.minimum(q3 + 1.5 * iqr, q4)

    data = np.array([lowerfence, q1, q2, q3, upperfence])
    data = np.round(data)
    data = data[:, ticklabel_skill_inds(split)]  # reorder skills in order of boxplot ticks
    nan_cols = np.isnan(data[2, :])
    data[:, nan_cols] = hide_val

    quartiles_dict = {}
    for i, q in enumerate(['lowerfence', 'q1', 'median', 'q3', 'upperfence']):
        quartiles_dict[q] = data[i, :]
    return quartiles_dict
