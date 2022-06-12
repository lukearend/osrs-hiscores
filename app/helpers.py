import base64
import json
import os
import pickle
import string
from pathlib import Path
from typing import OrderedDict, Any, Tuple, Dict

from src.common import download_s3_obj, osrs_skills
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
    return Path(__file__).resolve().parent / 'assets'


def load_icon_b64(skill: str) -> str:
    """ Load the icon for a skill as a base64-encoded string. """

    file = os.path.join(assets_dir(), 'icons', f'{skill}.png')
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


def mongodoc_to_player(doc: Dict[str, Any]) -> Dict[str, Any]:
    skills = osrs_skills(include_total=True)
    return {
        'username': doc['username'],
        'stats': {skill: lvl for skill, lvl in zip(skills, doc['stats'])},
        'clusterids': doc['clusterids']
    }


def get_trigger(callback_context) -> Tuple[str, Any]:
    if not callback_context.triggered:
        return None, None

    trigger = callback_context.triggered[0]
    propid = trigger['prop_id']
    value = trigger['value']

    # transform 'my-component.value' -> 'my-component'
    id = ''.join(propid.split('.')[:-1])

    # id is a stringified JSON map for pattern-matching callbacks
    try:
        id = json.loads(id)
    except json.JSONDecodeError:
        pass

    return id, value
