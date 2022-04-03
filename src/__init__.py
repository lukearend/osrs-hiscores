""" Contains knowledge shared across modules. """
import json
import os
import subprocess
from dataclasses import dataclass

from functools import cache
from pathlib import Path
import shlex
from typing import List, Any, Dict

import certifi as certifi
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError

from src.analytics.data import load_splits


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
def osrs_skills(include_total: bool = False) -> List[str]:
    """
    Load the list of OSRS skill names in an ordering for use throughout the project.
    :return: OSRS skills names, e.g. ['attack', 'defence', ...]
    """
    file = Path(__file__).resolve().parents[2] / "ref" / "osrs-skills.json"
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
    ref_file = Path(__file__).resolve().parents[2] / "ref" / "csv-api-stats.json"
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
