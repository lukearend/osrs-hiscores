""" Database utilities. """

import certifi
from pymongo import MongoClient
from pymongo.collection import Collection
from src.data.types import PlayerResults


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


def mongo_get_player(coll: Collection, username: str) -> PlayerResults:
    doc = coll.find_one({'_id': username.lower()})
    if not doc:
        return None
    return PlayerResults(
        username=doc['username'],
        clusterids=doc['clusterids'],
        stats=doc['stats']
    )
