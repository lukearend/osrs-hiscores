""" Contains knowledge shared across modules. """
import json
import os
import pickle
from dataclasses import dataclass

from functools import cache
from pathlib import Path
from subprocess import check_output
from typing import List, Dict, Any

import boto3
import certifi as certifi
import progressbar as progressbar
from botocore.exceptions import NoCredentialsError
from numpy.typing import NDArray
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError


@cache
def osrs_skills(include_total: bool = False) -> List[str]:
    """
    Load the list of OSRS skill names in a canonical ordering for use throughout
    this project. The ordering here is the same as that of the data returned by
    the CSV hiscores API.

    :return: list of OSRS stat names, e.g. ['attack', 'defence', ...]
    """
    skills = ['attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic',
              'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
              'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer', 'farming',
              'runecraft', 'hunter', 'construction']
    if include_total:
        skills.insert(0, 'total')
    return skills


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


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """
    username: str
    clusterids: Dict[str, int]  # resulting cluster ID for each split of the dataset
    stats: List[int]


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


def connect_mongo(url: str) -> Database:
    """ Connect to MongoDB instance at the given URL.

    :param url: connect to instance running at this URL
    :return: database containing project collection(s)
    """
    is_local = url.startswith("0.0.0.0") or url.startswith("localhost")
    mongo = MongoClient(url, tlsCAFile=None if is_local else certifi.where())
    db = mongo[global_db_name()]
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


def unpickle(file: str) -> Any:
    with open(file, 'rb') as f:
        return pickle.load(f)


def line_count(file: str) -> int:
    return int(check_output(['wc', '-l', file]).split()[0])


def global_db_name() -> str:
    return 'osrs-hiscores'


@cache
def osrs_minigames() -> List[str]:
    return ["bounty_hunter_hunter", "bounty_hunter_rogue", "clue_scrolls_all", "clue_scrolls_beginner",
            "clue_scrolls_easy", "clue_scrolls_medium", "clue_scrolls_hard", "clue_scrolls_elite",
            "clue_scrolls_master", "lms_rank", "soul_wars_zeal", "abyssal_sire", "alchemical_hydra",
            "barrows_chests", "bryophyta", "callisto", "cerberus", "chambers_of_xeric",
            "chambers_of_xeric_challenge_mode", "chaos_elemental", "chaos_fanatic", "commander_zilyana",
            "corporeal_beast", "crazy_archaeologist", "dagannoth_prime", "dagannoth_rex", "dagannoth_supreme",
            "deranged_archaeologist", "general_graardor", "giant_mole", "grotesque_guardians", "hespori",
            "kalphite_queen", "king_black_dragon", "kraken", "kreearra", "kril_tsutsaroth", "mimic", "nex",
            "nightmare", "phosanis_nightmare", "obor", "sarachnis", "scorpia", "skotizo", "tempoross",
            "the_gauntlet", "the_corrupted_gauntlet", "theatre_of_blood", "theatre_of_blood_hard_mode",
            "thermonuclear_smoke_devil", "tzkal_zuk", "tztok_jad", "venenatis", "vetion", "vorkath",
            "wintertodt", "zalcano", "zulrah"]
