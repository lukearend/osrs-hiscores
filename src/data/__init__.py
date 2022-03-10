""" Utilities for writing and loading data. """
import csv
import pickle
from dataclasses import dataclass
from plistlib import Dict
from typing import List

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from src.common import line_count, osrs_skills


@dataclass
class PlayerStatsData:
    """
    Represents a dataset of OSRS account skill levels.

    :usernames: usernames in dataset (correspond to rows)
    :skills: skills in dataset (correspond to columns)
    :levels: 2D array where each row gives a player's levels in each skill
    """
    usernames: List[str]  # usernames in dataset (correspond to rows)
    skills: List[str]     # skills in dataset (correspond to columns)
    levels: NDArray       # 2D array where each row gives a player's levels in each skill

@dataclass
class PlayerClustersData:
    """
    Represents the results of clustering runs on the OSRS account data set.

    :usernames: usernames in dataset (correspond to rows)
    :splits: the different data splits for which clustering was run (correspond to columns)
    :clusterids: 2D array where each row gives a player's assigned cluster ID for each split
    """
    usernames: List[str]
    splits: List[str]
    clusterids: NDArray


@dataclass
class ClusterCentroids:
    """
    Represents centroids for a set of clusters in OSR account space.

    :clusterids: cluster IDs corresponding to rows of centroid array
    :skills: skills corresponding to columns of centroid array
    :centroids: array where each row is the centroid of a cluster in OSRS account space

    """
    clusterids: List[int]
    skills: List[str]
    centroids: NDArray


def load_stats_data_csv(file: str, include_total=True) -> PlayerStatsData:
    """
    Load dataset of player skill levels from the CSV file created by the
    scraping process. Each row of the dataset is a vector of skill levels for
    a player with the columns corresponding to total level and the 23 OSRS
    skills. Level values are integers between 1 and 99, with -1 indicating
    data that is missing due to the player being unranked in a skill.

    :param file: load data from this CSV file
    :param include_total: whether to include total level column
    :return: PlayerStatsData object containing the skill levels dataset
    """
    print("loading player stats data...")
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)

        # CSV header consists of username followed by rank, level, and xp in each skill.
        # Here we just take 'level' columns for analysis, leaving behind rank and xp data.
        take_stats = [f"{s}_level" for s in osrs_skills(include_total)]
        take_cols = [header.index(s) for s in take_stats]

        usernames = []
        nplayers = line_count(file) - 1
        stats = np.zeros((nplayers, len(take_cols)), dtype='int')
        with tqdm(total=nplayers) as pbar:
            for i, line in enumerate(reader):
                usernames.append(line[0])
                stats[i, :] = [line[i] for i in take_cols]
                pbar.update(1)

    return PlayerStatsData(
        usernames=usernames,
        skills=osrs_skills(include_total),
        levels=stats
    )


def load_centroid_data(file: str) -> Dict[str, ClusterCentroids]:
    """
    Load dataset of cluster centroids resulting from the clustering runs on
    each split of the data. Each centroid is a vector is "OSRS skill" space
    representing the center of a cluster of similar accounts.

    :param file: load cluster centroids data from this file
    :return: map from split names to ClusterCentroids objects containing the
             centroids discovered for each split
    """
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_clusterids_data(file: str) -> PlayerClustersData:
    """
    Load dataset of cluster IDs for each player. Each player is assigned a
    cluster ID for each data split; ie, cluster IDs differ for a player
    when clustering is run on different subsets of account stats.

    :param file: load player cluster IDs from this CSV file
    :return: PlayerClustersData object containing the clustering results
             for players across all splits
    """
    with open(file, 'rb') as f:
        return pickle.load(f)
