import warnings
import pickle

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # dash_core_components is deprecated
    import dash_auth
from dash import Dash

from src.app.callbacks import add_callbacks
from src.app.components import build_layout
from src.data.db import connect_mongo
from src.data.io import load_pkl, download_s3_obj


def buildapp(app, mongo_url, appdata_coll, appdata_file, auth) -> Dash:
    """ Visualize clustering results for the OSRS hiscores. """

    player_coll = connect_mongo(mongo_url, appdata_coll)

    if appdata_file.startswith('s3://'):
        s3_bucket, obj_key = appdata_file.replace('s3://', '').split('/', maxsplit=1)
        app_data = pickle.loads(download_s3_obj(s3_bucket, obj_key))
    else:
        app_data = load_pkl(appdata_file)

    build_layout(app, app_data)
    add_callbacks(app, app_data, player_coll)

    if auth:
        auth_coll = connect_mongo(mongo_url, 'auth')
        auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
        dash_auth.BasicAuth(app, username_password_list=auth_pairs)
