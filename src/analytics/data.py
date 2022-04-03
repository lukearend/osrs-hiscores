""" Utilities for writing and loading data. """

import csv
import json
import os
import pickle
from functools import cache
from pathlib import Path
from typing import Dict, List, Any

import boto3
import numpy as np
import progressbar as progressbar
from botocore.exceptions import NoCredentialsError
from numpy.typing import NDArray
from tqdm import tqdm

from src import count_csv_rows, osrs_skills, DatasetSplit
from src.analytics import PlayerStatsData, PlayerClustersData, ClusterCentroids
from src.app import AppData


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
        nplayers = count_csv_rows(file, header=True)
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

    :param file: load player cluster IDs from this file
    :return: PlayerClustersData object containing the clustering results
             for players across all splits
    """
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_clusters_xyz(file: str) -> Dict[str, Dict]:  # TODO: becomes NDArray once umap params frozen
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_cluster_analytics(file: str) -> Dict[str, ClusterAnalytics]:
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_app_data(file: str) -> AppData:
    with open(file, 'rb') as f:
        return pickle.load(f)


@cache
def load_splits(file: str = None) -> List[DatasetSplit]:
    """
    Load metadata about splits of the dataset to use for this project.

    If `file` is provided, split information is loaded from there. Otherwise,
    if OSRS_SPLITS_FILE is set in the environment, splits are loaded from there.
    Otherwise the splits are loaded from a default location.

    :param file: load split information from this JSON file. Splits should be
                 given as a list of maps, each having a 'name' key giving a name
                 for the split a key 'skills' which is a list of the OSRS skills
                 to be included in that split of the dataset.
    :return: list of objects representing metadata about each split
    """
    if not file:
        file = os.getenv("OSRS_SPLITS_FILE", None)
    elif not file:
        file = Path(__file__).resolve().parents[2] / "ref" / "data_splits.json"

    splits = []
    with open(file, 'r') as f:
        for s in json.load(f):
            split = DatasetSplit(
                name=s['name'],
                skills=s['skills']
            )
            splits.append(split)

    return splits


def split_dataset(player_vectors: NDArray, split: str, has_total: bool = False, splits_file: str = None) -> DatasetSplit:
    for ds in load_splits(splits_file):
        if ds.name == split:
            break
    else:
        raise KeyError(split)

    all_skills = osrs_skills(include_total=has_total)
    keep_cols = [all_skills.index(skill) for skill in ds.skills]
    if has_total:
        keep_cols.insert(0, all_skills.index('total'))

    player_vectors = player_vectors[:, keep_cols]
    return player_vectors.copy()  # copy to make array C-contiguous which is needed by faiss


def download_from_s3(bucket: str, s3_file: str, local_file: str):
    """
    Download object from an S3 bucket, writing it to a local file.

    :param bucket: S3 bucket URL
    :param s3_file: S3 object key
    :param local_file: path to local file where object is written
    """
    print(f"downloading s3://{bucket}/{s3_file}")
    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=s3_file)
    size = response['ContentLength']
    progress = progressbar.progressbar.ProgressBar(maxval=size)
    progress.start()

    def update_progress(chunk):
        progress.update(progress.currval + chunk)

    try:
        s3.download_file(bucket, s3_file, local_file, Callback=update_progress)
    except FileNotFoundError:
        print("file not found")
    except NoCredentialsError:
        print("credentials not available")


def unpickle(file: str) -> Any:
    with open(file, 'rb') as f:
        return pickle.load(f)