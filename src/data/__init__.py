import pathlib
import pickle

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def load_hiscores_data():
    print("loading hiscores data... ", end='')

    data_file = pathlib.Path(__file__).resolve().parents[2] / 'data/processed/stats.pkl'
    with open(data_file, 'rb') as f:
        dataset = pickle.load(f)

    # Unpack dataset keys: row names, col names and data values themselves.
    usernames = dataset['usernames']
    cols = dataset['features']
    data = dataset['stats']

    # Create three separate arrays, one each for rank, level and xp data.
    rank_data = data[:, 0::3]
    level_data = data[:, 1::3]
    xp_data = data[:, 2::3]
    skills = [col_name[:-len('_rank')] for col_name in cols[::3]]

    # Promote the arrays to dataframes.
    ranks = pd.DataFrame(data=rank_data, index=usernames, columns=skills)
    levels = pd.DataFrame(data=level_data, index=usernames, columns=skills)
    xp = pd.DataFrame(data=xp_data, index=usernames, columns=skills)

    print("done")

    return ranks, levels, xp


def exclude_missing(data):
    if len(data.shape) == 1:
        return data[data != -1]

    elif len(data.shape) == 2:
        keep_inds = []
        for i, row in enumerate(np.array(data)):
            if -1 in row or np.any(np.isnan(row)):
                continue
            keep_inds.append(i)
        return data[keep_inds]


def correlate_skills(skill_a, skill_b):
    levels_a = stats[:, features[skill_a + '_level']]
    levels_b = stats[:, features[skill_b + '_level']]
    keep_inds_a = levels_a > 0
    keep_inds_b = levels_b > 0
    keep_inds = np.logical_and(keep_inds_a, keep_inds_b)
    levels_a = levels_a[keep_inds]
    levels_b = levels_b[keep_inds]
    r_value, _ = pearsonr(levels_a, levels_b)
    return r_value
