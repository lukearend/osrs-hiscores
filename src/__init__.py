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


def load_skill_list() -> List[str]:
    splits_file = Path(__file__).resolve().parent.parent / "reference" / "osrs_skills.csv"
    with open(splits_file, 'r') as f:
        reader = csv.reader(f)
        return [line[0] for line in reader]


def load_kmeans_params() -> Dict[str, int]:
    params_file = Path(__file__).resolve().parent.parent / 'reference/kmeans_params.json'
    with open(params_file, 'r') as f:
        return json.load(f)


def load_umap_params() -> Dict[str, int]:
    params_file = Path(__file__).resolve().parent.parent / 'reference/umap_params.json'
    with open(params_file, 'r') as f:
        return json.load(f)


def load_stats_data(file: str) -> Tuple[List[str], List[str], NDArray]:
    print("loading player stats data...")
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)

        statnames = []
        for field in header[2::3]:
            statnames.append(field[:-len('_level')])

        nplayers = line_count(file) - 1
        usernames = np.zeros(nplayers, dtype='<U12')
        stats = np.zeros((nplayers, len(statnames)), dtype='int')

        with tqdm(total=nplayers) as pbar:
            for i, line in enumerate(reader):
                usernames[i] = line[0]
                stats[i, :] = [int(i) for i in line[2::3]]  # take levels, drop rank and xp columns
                pbar.update(1)

    return usernames, statnames, stats


@dataclass
class DataSplit:
    name: str
    nskills: int
    skills: List[str]
    skill_inds: List[int]


def load_skill_splits() -> List[DataSplit]:
    splits_file = Path(__file__).resolve().parent.parent / "reference" / "data_splits.json"
    with open(splits_file, 'r') as f:
        split_config = json.load(f)

    split_names: List[str] = split_config["names"]
    skills_per_split: Dict[str, List] = split_config["skills"]
    all_skills = load_skill_list()[1:]  # drop total level

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


def load_centroid_data(file: str) -> Dict[str, NDArray]:
    splits = load_skill_splits()

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

    centroids_per_split = {}
    for split in splits:
        split_centroids = np.zeros_like(centroids[split.name])
        for i, cid in enumerate(clusterids[split.name]):
            split_centroids[cid, :] = centroids[split.name][i]
        centroids_per_split[split.name] = split_centroids
    return centroids_per_split


def load_clusterids_data(file):
    print("loading cluster IDs...")
    num_players = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        splits = header[1:]

        usernames = np.zeros(num_players, dtype='<U12')
        cluster_ids = np.zeros((num_players, len(splits)), dtype='int')
        for i in tqdm(range(num_players)):
            line = next(reader)
            usernames[i] = line[0]
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
        print(f"file not found")
    except NoCredentialsError:
        print(f"credentials not available")
