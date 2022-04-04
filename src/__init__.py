""" Common knowledge. """

import json
import os
import subprocess
from dataclasses import dataclass

from functools import cache
from pathlib import Path
import shlex
from typing import List, Any, Dict

import certifi as certifi
from numpy.typing import NDArray
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError


DB_NAME = 'osrs-hiscores'


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """
    username: str
    clusterids: Dict[str, int]  # resulting cluster ID for each split of the dataset
    stats: List[int]


@dataclass
class DatasetSplit:
    """ Represents a "split" of the dataset, or subset of skill columns to be
    taken as clustering features. This allows us to choose which skills are
    involved in the account distance calculation. The data pipeline for this
    project will be run on each split of the data defined in ref/splits.json.
    """
    name: str
    skills: List[str]


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


@cache
def osrs_skills(include_total: bool = False) -> List[str]:
    """
    Load the list of OSRS skill names in an ordering for use throughout the project.
    :return: OSRS skills names, e.g. ['attack', 'defence', ...]
    """
    file = Path(__file__).resolve().parents[1] / "ref" / "osrs-skills.json"
    with open(file, 'r') as f:
        skills = json.load(f)
    if include_total:
        skills.insert(0, 'total')
    return skills


@cache
def csv_api_stats() -> List[str]:
    """
    Load the list of header fields returned from the OSRS hiscores CSV API.
    :return: header fields, e.g. ['total_rank', 'total_level', 'total_xp', ...]
    """
    ref_file = Path(__file__).resolve().parents[1] / "ref" / "csv-api-stats.json"
    with open(ref_file, 'r') as f:
        return json.load(f)


def connect_mongo(url: str) -> Database:
    """ Connect to MongoDB instance at the given URL.

    :param url: connect to instance running at this URL
    :return: database containing project collection(s)
    """
    is_local = any([s in url for s in ['127.0.0.1', '0.0.0.0', 'localhost']])
    mongo = MongoClient(url, tlsCAFile=None if is_local else certifi.where(), serverSelectionTimeoutMS=5000)
    db = mongo[DB_NAME]
    try:
        db.command('ping')
    except ServerSelectionTimeoutError:
        raise ValueError(f"could not connect to mongodb at {url}{', is the container running?' if is_local else ''}")
    return db


def player_results_to_mongodoc(player: PlayerResults) -> Dict[str, Any]:
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'clusterids': player.clusterids,
        'stats': player.stats
    }


def mongodoc_to_player_results(doc: Dict[str, Any]) -> PlayerResults:
    return PlayerResults(
        username=doc['username'],
        clusterids=doc['clusterids'],
        stats=doc['stats']
    )


def env_var(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError as e:
        raise ValueError(f"{e} is not set in environment")


def count_csv_rows(file: str, header=True) -> int:
    cmd = f"wc -l {file}"
    stdout = subprocess.check_output(shlex.split(cmd))
    n = int(stdout.decode().strip().split()[0])  # stdout returns number and filename
    return n - 1 if header else n
