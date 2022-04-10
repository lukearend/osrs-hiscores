""" Code for building app dependencies. """

from dataclasses import dataclass
from typing import List, Dict, Tuple, Any

import certifi
import pandas as pd
import xarray as xr
from pymongo import MongoClient
from pymongo.collection import Collection


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """

    username: str
    stats: List[int]                       # includes total level
    clusterids: Dict[int, Dict[str, int]]  # cluster ID for each split of the dataset, for each k


@dataclass
class SplitData:
    """ App data for one split of the dataset. """

    skills: List[str]                # length nskills in split
    cluster_quartiles: xr.DataArray  # shape (5, nclusters, nskills + 1), includes total level
    cluster_centroids: pd.DataFrame  # shape (nclusters, nskills)
    cluster_xyz: pd.DataFrame        # shape (nclusters, 3)
    cluster_sizes: List[int]         # length nclusters
    cluster_uniqueness: List[float]  # length nclusters
    xyz_axlims: Dict[str, Tuple[float, float]]


def connect_mongo(url: str, collection: str) -> Collection:
    """ Connect to MongoDB instance at the given URL and return a collection. """

    is_local = any([s in url for s in ['localhost', '127.0.0.1', '0.0.0.0']])
    mongo = MongoClient(url, tlsCAFile=None if is_local else certifi.where())
    db = mongo['osrs-hiscores']
    try:
        db.command('ping')
    except Exception:
        msg = f"could not connect to mongodb at {url}"
        if is_local:
            msg += ", is the Docker container running?"
        raise ValueError(msg)
    return db[collection]


def player_to_mongodoc(player: PlayerResults):
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'stats': player.stats
    }


def mongodoc_to_player(doc: Dict[str, Any]) -> PlayerResults:
    clusterid_results = {int(k): ids_dict for k, ids_dict in doc['clusterids'].items()}
    return PlayerResults(
        username=doc['username'],
        clusterids=clusterid_results,
        stats=doc['stats']
    )


def update_results_doc(username: str, k: int, clusterids: Dict[str, int]):
    return {'_id': username.lower()}, {'$set': {f'clusterids.{k}': clusterids}}
