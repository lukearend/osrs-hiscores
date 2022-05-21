""" Shared definitions. """

import json
import warnings
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import List

import boto3
import certifi
from pymongo import MongoClient
from pymongo.collection import Collection
from tqdm import TqdmWarning, tqdm


@lru_cache()
def osrs_skills(include_total: bool = False) -> List[str]:
    """ Load the list of OSRS skills in an order for use throughout the project. """

    file = Path(__file__).resolve().parents[1] / "ref" / "osrs-skills.json"
    with open(file, 'r') as f:
        skill_names = json.load(f)
    if include_total:
        skill_names.insert(0, 'total')
    return skill_names


@lru_cache()
def csv_api_stats() -> List[str]:
    """ Load the list of header fields returned from the OSRS hiscores CSV API. """

    file = Path(__file__).resolve().parents[1] / "ref" / "csv-api-stats.json"
    with open(file, 'r') as f:
        stat_names = json.load(f)
        assert stat_names[:3] == ['total_rank', 'total_level', 'total_xp']
        return stat_names


@lru_cache()
def download_s3_obj(bucket: str, obj_key: str) -> bytes:
    """ Download raw object from an S3 bucket with progress bar. """

    warnings.filterwarnings("ignore", category=TqdmWarning)  # supress warning from float iteration

    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=obj_key)
    size = response['ContentLength']

    print(f"downloading s3://{bucket}/{obj_key}")
    f = BytesIO()
    with tqdm(total=size, unit='B', unit_scale=True) as pbar:
        s3.download_fileobj(bucket, obj_key, f,
                            Callback=lambda n: pbar.update(n))

    f.seek(0)  # put cursor back at beginning of file
    return f.read()


def connect_mongo(url: str, collection: str = None) -> Collection:
    """ Get a handle to the MongoDB instance at the given URL. """

    is_local = any([s in url for s in ['localhost', '127.0.0.1']])
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