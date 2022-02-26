import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from subprocess import check_output
from typing import List, Dict, Tuple

import boto3
import numpy as np
import progressbar as progressbar
from botocore.exceptions import NoCredentialsError
from numpy.typing import NDArray
from tqdm import tqdm


def line_count(file: str) -> int:
    return int(check_output(['wc', '-l', file]).split()[0])


def osrs_statnames() -> List[str]:
    """
    Load the list of OSRS stats in a canonical ordering. This includes
    total level and the following 23 skills:
        Attack, Strength, Defence, Ranged, Magic, Prayer, Hitpoints
        Agility, Construction, Cooking, Crafting, Farming, Firemaking,
        Fishing, Fletching, Herblore, Hunter, Mining, Runecraft,
        Slayer, Smithing, Thieving, and Woodcutting

    :return: list of OSRS skill names
    """
    splits_file = Path(__file__).resolve().parents[2] / "reference" / "osrs_skills.csv"
    with open(splits_file, 'r') as f:
        reader = csv.reader(f)
        return [line[0] for line in reader]


@dataclass
class DataSplit:
    name: str
    nskills: int
    skills: List[str]
    skill_inds: List[int]  # index of each skill in the canonical ordering


def skill_splits() -> List[DataSplit]:
    """
    Load metadata about the three splits of the dataset used throughout:
    1) "all": player vector includes all skills
    2) "cb": player vector includes combat skills only
    3) "noncb": player vector includes non-combat skills only

    :return: list of objects representing metadata about each split
    """
    splits_file = Path(__file__).resolve().parents[2] / "reference" / "data_splits.json"
    with open(splits_file, 'r') as f:
        split_config = json.load(f)

    split_names: List[str] = split_config["names"]
    skills_per_split: Dict[str, List] = split_config["skills"]
    all_skills = osrs_statnames()[1:]  # drop total level

    splits = []
    for split_name in split_names:
        skills = skills_per_split[split_name]
        split = DataSplit(
            name=split_name,
            nskills=len(skills),
            skills=skills,
            skill_inds=[all_skills.index(s) for s in skills]
        )
        splits.append(split)
    return splits


def split_dataset(data: NDArray, split: DataSplit) -> NDArray:
    player_vectors = data[:, split.skill_inds]
    return player_vectors.copy()  # copy to make C-contiguous array (needed by faiss)


def load_stats_data(file: str) -> Tuple[List[str], List[str], NDArray]:
    """
    Load dataset of player stats. Each row of the dataset is a vector of player
    stats and the columns correspond to total level and the 23 OSRS skills.
    Skill level values are integers between 1 and 99, with values of -1 indicating
    data that is missing due to a player being unranked in a skill.

    :param file: path to CSV file
    :return: array of player usernames
    :return: list of OSRS stat names
    :return: 2D array of player stat vectors
    """
    print("loading player stats data...")
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)

        statnames = []
        for field in header[2::3]:
            statnames.append(field[:-len('_level')])

        nplayers = line_count(file) - 1
        usernames = []
        stats = np.zeros((nplayers, len(statnames)), dtype='int')

        with tqdm(total=nplayers) as pbar:
            for i, line in enumerate(reader):
                usernames.append(line[0])
                stats[i, :] = [int(i) for i in line[2::3]]  # take levels, drop rank and xp columns
                pbar.update(1)

    return usernames, statnames, stats


def load_centroid_data(file: str) -> Dict[str, NDArray]:
    """
    Load dataset of cluster centroids resulting from the clustering runs on
    each split of the data. Each centroid is a vector is "OSRS skill" space
    representing the center of a cluster of similar accounts.

    :param file: path to CSV file
    :return: 2D array where row N is the centroid for cluster N
    """
    with open(file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # discard header

        clusterids = defaultdict(list)
        centroids = defaultdict(list)
        for i, line in enumerate(reader):
            splitname = line[0]
            clusterid = int(line[1])
            centroid = [float(v) for v in line[2:] if v != '']
            clusterids[splitname].append(clusterid)
            centroids[splitname].append(centroid)

    splits = skill_splits()
    centroids_per_split = {}
    for split in splits:
        split_centroids = np.zeros_like(centroids[split.name])
        for i, cid in enumerate(clusterids[split.name]):
            split_centroids[cid, :] = centroids[split.name][i]
        centroids_per_split[split.name] = split_centroids
    return centroids_per_split


def load_clusterids_data(file: str) -> Tuple[List[str], List[str], NDArray]:
    """
    Load dataset of cluster IDs for each player. Each player is assigned a
    cluster ID for each data split; ie, cluster IDs differ for a player
    when clustering is run on different subsets of account stats.

    :param file: path to CSV file
    :return: array of player usernames
    :return: list of split names
    :return: 2D array where each row is the cluster IDs for a player
    """
    print("loading cluster IDs...")
    nplayers = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        splits = header[1:]

        usernames = []
        cluster_ids = np.zeros((nplayers, len(splits)), dtype='int')
        for i in tqdm(range(nplayers)):
            line = next(reader)
            usernames.append(line[0])
            cluster_ids[i, :] = line[1:]

    return usernames, splits, cluster_ids


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
