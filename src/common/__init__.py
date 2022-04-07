""" Common knowledge. """

import json
from dataclasses import dataclass

from functools import cache
from pathlib import Path
from typing import List, OrderedDict, Dict, Any

import certifi
from pymongo import MongoClient
from pymongo.database import Database


@dataclass
class Player:
    """ Stats and clustering results for a player. """
    username: str
    clusterid: Dict[str, int]  # cluster ID for each split of the dataset
    stats: List[int]


@cache
def osrs_skills(include_total: bool = False) -> List[str]:
    """ Load the list of OSRS skill names. """

    file = Path(__file__).resolve().parents[2] / "ref" / "osrs-skills.json"
    with open(file, 'r') as f:
        skills = json.load(f)
    if include_total:
        skills.insert(0, 'total')
    return skills


@cache
def load_splits(file: str = None) -> OrderedDict[str, List[str]]:
    """ Load the skill 'splits' of the dataset for use throughout the project.
    Each split is a subset of skills to be used as features for clustering. """

    if file is None:
        file = Path(__file__).resolve().parents[2] / "ref" / "splits.json"
    return json.loads(file, object_pairs_hook=OrderedDict)


def connect_mongo(url: str) -> Database:
    """ Connect to MongoDB instance at the given URL. """

    is_local = any([s in url for s in ['127.0.0.1', '0.0.0.0', 'localhost']])
    mongo = MongoClient(url, tlsCAFile=None if is_local else certifi.where(), serverSelectionTimeoutMS=10000)
    db = mongo['osrs-hiscores']
    try:
        db.command('ping')
    except Exception:
        raise ValueError(f"could not connect to mongodb at {url}{', is the container running?' if is_local else ''}")
    return db


def player_to_mongodoc(player: Player) -> Dict[str, Any]:
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'clusterids': player.clusterid,
        'stats': player.stats
    }


def mongodoc_to_player(doc: Dict[str, Any]) -> Player:
    return Player(
        username=doc['username'],
        clusterid=doc['clusterids'],
        stats=doc['stats']
    )
