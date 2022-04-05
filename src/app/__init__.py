from dataclasses import dataclass
from typing import Dict, List, Any

import certifi as certifi
from numpy.typing import NDArray
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError

from src import DatasetSplit, DB_NAME, PlayerResults


@dataclass
class ClusterData:
    """ Contains app data for a set of clusters. """

    xyz: NDArray
    sizes: NDArray
    centroids: NDArray
    quartiles: NDArray
    uniqueness: NDArray


@dataclass
class SplitData:
    """ Contains app data for one split of the dataset. """

    skills: List[str]
    clusterdata: ClusterData
    axlims: NDArray


@dataclass
class AppData:
    """ Contains all data needed to run Dash app. """

    splitnames: List[DatasetSplit]
    splitdata: Dict[str, SplitData]


@dataclass
class BoxplotLayout:
    """ Contains layout information for rendering boxplot for a specific split. """
    ticklabels: List[str]
    tickxoffset: float


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
