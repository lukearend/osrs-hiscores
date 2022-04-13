""" Code for building app dependencies. """

from dataclasses import dataclass
from typing import List, Dict, Tuple, Any

import certifi
import pandas as pd
import xarray as xr
from numpy.typing import NDArray
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """

    username: str
    stats: List[int]                       # includes total level
    clusterids: Dict[str, int]  # cluster ID for each split of the dataset


@dataclass
class SplitData:
    """ App data for one split of the dataset. """

    skills: List[str]                # length nskills in split
    cluster_quartiles: xr.DataArray  # shape (5, nclusters, nskills + 1), includes total level
    cluster_centroids: pd.DataFrame  # shape (nclusters, nskills)
    cluster_xyz: pd.DataFrame        # shape (nclusters, 3)
    cluster_sizes: NDArray           # length nclusters
    cluster_uniqueness: NDArray      # length nclusters
    xyz_axlims: Dict[str, Tuple[float, float]]


def connect_mongo(url: str, collection: str = None) -> Collection:
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
    if collection is None:
        return db
    return db[collection]


def player_to_mongodoc(player: PlayerResults):
    doc = {
        '_id': player.username.lower(),
        'username': player.username,
        'stats': player.stats
    }
    if player.clusterids:
        doc['clusterids'] = {str(k): ids_dict for k, ids_dict in player.clusterids.items()}
    else:
        doc['clusterids'] = {}
    return doc


# def mongo_get_player(coll: Collection, username: str) -> PlayerResults:
#     doc = coll.find_one({'_id': username.lower()})
#     if not doc:
#         return None
#     clustering_results = {int(k): ids_dict for k, ids_dict in doc['clusterids'].items()}
#     return PlayerResults(
#         username=doc['username'],
#         clusterids=clustering_results,
#         stats=doc['stats']
#     )


def mongo_get_player(stats_coll: Collection, clusterids_coll: Collection, username: str) -> PlayerResults:
    stats_doc = stats_coll.find_one({'_id': username.lower()})
    clusterids_doc = clusterids_coll.find_one({'_id': username.lower()})
    if not stats_doc or not clusterids_doc:
        return None
    return PlayerResults(
        username=stats_doc['username'],
        clusterids=clusterids_doc['clusterids'],
        stats=stats_doc['stats']
    )


def player_to_stats_doc(player):
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'stats': player.stats
    }


def player_to_clusterids_doc(player):
    return {
        '_id': player.username.lower(),
        'username': player.username,
        'clusterids': player.clusterids
    }