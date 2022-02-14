#!/usr/bin/env python3

""" Visualize hiscores clustering results with a Dash application. """

import os

from dash import Dash
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dash_bootstrap_components import themes

from app import get_env_variable
from app.data import load_appdata_local, load_appdata_s3
from app.layout import build_layout
from app.callbacks import add_callbacks

env_mode = os.getenv("OSRS_APP_ENV", 'development')
if env_mode in ['production', 'test']:
    bucket = get_env_variable("OSRS_APPDATA_S3BUCKET")
    obj_key = get_env_variable("OSRS_APPDATA_S3KEY")
    app_data = load_appdata_s3(bucket, obj_key)
    debug = False
else:
    app_data = load_appdata_local()
    debug = True

mongo_url = get_env_variable("OSRS_MONGO_URI")
mongo = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
db = mongo['osrs-hiscores']
try:
    db.command('ping')
except ServerSelectionTimeoutError:
    raise ValueError("could not connect to mongodb")
player_db = db['players']

app = Dash(__name__,
           title="OSRS player clusters",
           external_stylesheets=[themes.BOOTSTRAP])
app = build_layout(app, app_data)
app = add_callbacks(app, app_data, player_db)

app.run_server(debug=debug)
