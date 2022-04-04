""" Utilities for writing and loading data. """

import csv
import pickle
from typing import Dict, Any

import boto3
import numpy as np
import progressbar as progressbar
from botocore.exceptions import NoCredentialsError
from tqdm import tqdm

from src import count_csv_rows, osrs_skills
from src.analytics import PlayerStatsDataset, PlayerClustersData, ClusterCentroids, ClusterAnalytics
from src.app import AppData


def load_stats_data_csv(file: str, include_total=True) -> PlayerStatsDataset:
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

    return PlayerStatsDataset(
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


def load_clusters_xyz(file: str) -> NDArray
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_cluster_analytics(file: str) -> Dict[str, ClusterAnalytics]:
    with open(file, 'rb') as f:
        return pickle.load(f)


def load_app_data(file: str) -> AppData:
    with open(file, 'rb') as f:
        return pickle.load(f)


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
