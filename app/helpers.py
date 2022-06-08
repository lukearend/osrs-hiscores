import base64
import json
import os
import pickle
import string
from pathlib import Path
from typing import OrderedDict

from src.common import download_s3_obj
from src.analysis.appdata import SplitResults
from src.analysis.io import load_pkl


VALID_UNAME_CHARS = (string.ascii_lowercase +
                     string.ascii_uppercase +
                     string.digits + ' -_')


def is_valid_username(username: str) -> bool:
    """ Check whether a string is a valid OSRS username. """

    if not username:
        return False
    if len(username) > 12:
        return False
    if username.strip(VALID_UNAME_CHARS):
        return False
    return True


def assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / 'assets'


def load_icon_b64(skill: str) -> str:
    """ Load the icon for a skill as a base64-encoded string. """

    file = os.path.join(assets_dir(), 'icons', skill + '.png')
    with open(file, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def load_app_data(path: str) -> OrderedDict[str, SplitResults]:
    """ Load app data from S3 bucket or local path. """

    if path.startswith('s3://'):
        blob = download_s3_obj(url=path)
        app_data = pickle.loads(blob)
    else:
        app_data = load_pkl(path)

    return app_data


def triggered_id(callback_context) -> str:
    """ Get the ID of the component that triggered a callback. """

    triggered = callback_context.triggered
    if not triggered:
        return None
    propid = triggered[0]['prop_id']
    suffix = '.' + propid.split('.')[-1]
    id = propid[:-len(suffix)]

    # Pattern-matching component IDs are a JSON-serialized dict.
    try:
        return json.loads(id)
    except json.JSONDecodeError:
        return id
