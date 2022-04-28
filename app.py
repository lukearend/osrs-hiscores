#!/usr/bin/env python3

""" Dash application to visualize clustering results for the OSRS hiscores. """

import os
import pickle
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # supress deprecation warning from dash_core_components
    import dash_auth
import dash_bootstrap_components as dbc
from dash import Dash

from src.app.layout import build_layout
from src.app.callbacks import add_callbacks
from src.analysis.app import connect_mongo
from src.analysis.data import load_pkl
from src import download_s3_obj


mongo_url = os.getenv("OSRS_MONGO_URI", "localhost:27017")
coll_name = os.getenv("OSRS_APPDATA_COLL", "players")
deployment = os.getenv("OSRS_DEPLOY_MODE", 'local')
data_file = os.getenv("OSRS_APPDATA_FILE", None)
auth = os.getenv("OSRS_REQUIRE_AUTH", None)
debug = os.getenv("OSRS_DEBUG_MODE", None)

auth = True if auth is not None and auth.lower() != 'false' else False
debug = True if debug is None else debug.lower() != 'false'
if deployment == 'cloud':
    if data_file is None:
        raise ValueError("missing config variable: OSRS_APPDATA_FILE")
elif deployment == 'local':
    if data_file is None:
        data_file = str(Path(__name__).resolve().parent / "data" / "interim" / "appdata.pkl")
else:
    raise ValueError(f"unrecognized deployment type '{deployment}' (options: 'local', 'cloud')")


player_coll = connect_mongo(mongo_url, coll_name)
if deployment == 'cloud':
    s3_bucket, obj_key = data_file.replace('s3://', '').split('/', maxsplit=1)
    app_data = pickle.loads(download_s3_obj(s3_bucket, obj_key))
else:
    app_data = load_pkl(data_file)

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
build_layout(app, app_data)
add_callbacks(app, app_data, player_coll)

if auth:
    auth_coll = connect_mongo(mongo_url, 'auth')
    auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
    dash_auth.BasicAuth(app, username_password_list=auth_pairs)


server = app.server
app.run_server(debug=debug)
