import base64
import pickle
from functools import lru_cache
from typing import OrderedDict

from app import app
from src.common import download_s3_obj
from src.data.io import load_pkl
from src.data.types import SplitResults


@lru_cache()
def load_icon_b64(skill: str):
    file = app.get_asset_url(f"icons/{skill}.png")
    with open(file, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


@lru_cache()
def load_app_data(path) -> OrderedDict[str, SplitResults]:
    """ Load pickled app data from S3 bucket or local path. """

    if path.startswith('s3://'):
        s3_bucket, obj_key = path.replace('s3://', '').split('/', maxsplit=1)
        blob = download_s3_obj(s3_bucket, obj_key)
        app_data = pickle.loads(blob)
    else:
        app_data = load_pkl(path)

    return app_data
