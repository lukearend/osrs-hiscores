import string
import pickle
from functools import cache
from io import BytesIO
from numbers import Number
from pathlib import Path
from typing import List, Dict

import boto3

from src.analysis.app import SplitData
from src.analysis.data import load_json, load_pkl


STATS_COLL = 'stats'
CLUSTERIDS_COLL = 'clusterids'


def default_n_neighbors(split):
    return {'all': 5, 'cb': 15, 'noncb': 5}[split]


def default_min_dist(split):
    return {'all': 0.25, 'cb': 0.25, 'noncb': 0.0}[split]


def skill_upper(skill):
    return skill[0].upper() + skill[1:]


def format_skill(skill):
    return f"{skill_upper(skill)} level"


def get_color_label(skill):
    return f"{skill_upper(skill)}\nlevel"


def get_color_range(skill):
    return [500, 2277] if skill == 'total' else [1, 99]


def get_point_size(ptsize_name):
    return {'small': 1, 'medium': 2, 'large': 3}[ptsize_name]


def get_level_tick_marks(skill):
    if skill == 'total':
        return {i: str(i) for i in [1, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2277]}
    return {i: str(i) for i in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]}


def validate_username(username):
    if len(username) > 12:
        return False
    if username.strip(string.ascii_lowercase + string.ascii_uppercase + string.digits + ' -_'):
        return False
    return True


def assets_dir() -> Path:
    return Path(__file__).resolve().parent / 'assets'


@cache
def load_params() -> Dict[str, List[Number]]:
    return load_json(assets_dir() / 'params.json')


@cache
def load_table_layout() -> List[List[str]]:
    return load_json(assets_dir() / 'table_layout.json')


@cache
def load_boxplot_tick_labels(split: str) -> List[str]:
    return load_json(assets_dir() / 'boxplot_ticklabels.json')[split]


@cache
def load_boxplot_x_offsets(split: str) -> float:
    return load_json(assets_dir() / 'boxplot_offsets.json')[split]


@cache
def ticklabel_skill_inds(split: str) -> List[int]:
    k = load_params()['k'][0]
    nn = load_params()['n_neighbors'][0]
    min_dist = load_params()['min_dist'][0]
    split_skills = load_app_data(k, nn, min_dist)[split].skills
    tick_labels = load_boxplot_tick_labels(split)
    return [split_skills.index(skill) for skill in tick_labels]


@cache
def load_app_data(k, n_neighbors, min_dist) -> Dict[str, SplitData]:
    base = Path(__file__).resolve().parents[1] / "data" / "interim" / "appdata"
    return load_pkl(f"{base}-{k}-{n_neighbors}-{min_dist}.pkl")


def load_app_data_s3(bucket: str, obj_key: str) -> Dict[str, SplitData]:
    print("downloading app data...", end=' ', flush=True)
    s3 = boto3.client('s3')
    f = BytesIO()
    s3.download_fileobj(bucket, obj_key, f)
    f.seek(0)
    return pickle.load(f)
