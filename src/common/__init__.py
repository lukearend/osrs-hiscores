""" Contains knowledge shared across modules. """

import csv
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from subprocess import check_output
from typing import List, Dict, Tuple, Any

import boto3
import certifi as certifi
import numpy as np
import progressbar as progressbar
from botocore.exceptions import NoCredentialsError
from numpy.typing import NDArray
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError
from tqdm import tqdm


@lru_cache()
def osrs_skills() -> List[str]:
    """
    Load the list of OSRS skill names in a canonical ordering for use throughout
    this project. The ordering here is the same as that of the data returned by
    the CSV hiscores API.

    :return: list of OSRS stat names, e.g. ['attack', 'defence', ...]
    """
    return ['attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic',
            'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
            'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer', 'farming',
            'runecraft', 'hunter', 'construction']


@dataclass
class DatasetSplit:
    """ Represents a "split" of the dataset, or subset of skill columns to be
    taken as clustering features. This allows us to choose which skills are
    involved in the account distance calculation. The data pipeline for this
    project will be run on each split of the data defined in ref/splits.json.
    """
    name: str
    nskills: int
    skills: List[str]
    skillinds: List[int]  # index of each skill in the canonical skill ordering


@lru_cache()
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
                skills=s['skills'],
                nskills=len(s['skills']),
                skillinds=[osrs_skills.index(skill) for skill in s['skills']]
            )
            splits.append(split)

    return splits


def split_dataset(data: NDArray, splitname: str) -> NDArray:
    split = splitinfo(splitname)
    player_vectors = data[:, split.skillinds]
    return player_vectors.copy()  # copy to make C-contiguous array (needed by faiss)


@dataclass
class PlayerData:
    """ Stats and clustering results for a player. """
    username: str
    clusterids: Dict[str, int]  # resulting cluster ID for each split of the dataset
    stats: List[int]


def playerdata_to_mongodoc(player: PlayerData) -> Dict[str, Any]:
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'clusterids': player.clusterids,
        'stats': player.stats
    }


def mongodoc_to_playerdata(doc: Dict[str, Any]) -> PlayerData:
    return PlayerData(
        username=doc['username'],
        clusterids=doc['clusterids'],
        stats=doc['stats']
    )


def connect_mongo(url: str) -> Database:
    """ Connect to MongoDB instance at the given URL.

    :param url: connect to instance running at this URL
    :return: database containing player collection
    """
    is_local = url.startswith("0.0.0.0") or url.startswith("localhost")
    mongo = MongoClient(url, tlsCAFile=None if is_local else certifi.where())
    db = mongo['osrs-hiscores']
    try:
        db.command('ping')
    except ServerSelectionTimeoutError:
        raise ValueError(f"could not connect to mongodb at {url}")
    return db


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


def env_var(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError as e:
        raise ValueError(f"{e} is not set in environment")


def line_count(file: str) -> int:
    return int(check_output(['wc', '-l', file]).split()[0])
