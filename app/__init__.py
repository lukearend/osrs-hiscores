import string
import json
import pickle
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import List

import boto3

from src.results import AppData


_username_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + ' -_'
def validate_username(username):
    if len(username) > 12:
        return False
    if username.strip(_username_chars):
        return False
    return True


def default_n_neighbors(split):
    return {'all': 5, 'cb': 15, 'noncb': 5}[split]


def default_min_dist(split):
    return {'all': 0.25, 'cb': 0.25, 'noncb': 0.00}[split]


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
    else:
        return {i: str(i) for i in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]}


@dataclass
class BoxplotLayout:
    """ Contains layout information for rendering boxplot for a specific split. """
    ticklabels: List[str]
    tickxoffset: float


@lru_cache()
def load_boxplot_layout(split: str) -> BoxplotLayout:
    """
    Load layout information for boxplot for the given split.
    :split: name of the split being displayed
    :return: split-specific object containing layout info for rendering boxplot
      -
      - x offset value for the icons used as tick labels
    """
    ticklabels_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_ticklabels.json'
    with open(ticklabels_file, 'r') as f:
        tick_labels = json.load(f)[split]

    offsets_file = Path(__file__).resolve().parent / 'assets' / 'boxplot_offsets.json'
    with open(offsets_file, 'r') as f:
        x_offset = json.load(f)[split]

    return BoxplotLayout(
        ticklabels=tick_labels,
        tickxoffset=x_offset
    )


@lru_cache()
def load_table_layout() -> List[List[str]]:
    """
    Load layout for the skills to be displayed in skill tables.
    :return: list of lists where each inner list gives the skills in a table row
    """
    layout_file = Path(__file__).resolve().parent / 'assets' / 'table_layout.json'
    with open(layout_file, 'r') as f:
        return json.load(f)


def load_appdata_local(file: str = None) -> AppData:
    """
    Load the object containing all data needed to drive this Dash application.
    :param file: load from this local file (optional, otherwise uses default location)
    :return: application data object built by project source code
    """
    if not file:
        file = Path(__file__).resolve().parents[1] / 'data' / 'processed' / 'app_data.pkl'
    with open(file, 'rb') as f:
        app_data: AppData = pickle.load(f)
        return app_data


def load_appdata_s3(bucket: str, obj_key: str) -> AppData:
    """
    Load the object containing all data needed to drive this Dash application.
    :bucket: AWS S3 bucket to download app data from
    :obj_key: key to object to download within bucket
    :return: application data object built by project source code
    """
    print("downloading app data...", end=' ', flush=True)
    f = BytesIO()
    s3 = boto3.client('s3')
    s3.download_fileobj(bucket, obj_key, f)
    print("done")
    f.seek(0)
    app_data: AppData = pickle.load(f)
    return app_data
