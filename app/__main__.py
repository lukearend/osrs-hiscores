#!/usr/bin/env python3

""" Visualize hiscores clustering results with a Dash application. """

import os

from dash import Dash
from dash_bootstrap_components import themes

from src.common import env_var, connect_mongo
from app import load_appdata_local, load_appdata_s3
from app.layout import build_layout
from app.callbacks import add_callbacks

envmode = os.getenv("OSRS_APP_ENV", 'development')
if envmode in ['production', 'test']:
    bucket = env_var("OSRS_APPDATA_S3BUCKET")
    obj_key = env_var("OSRS_APPDATA_S3KEY")
    appdata = load_appdata_s3(bucket, obj_key)
    debug = False
else:
    appdata = load_appdata_local(os.getenv("OSRS_APPDATA_LOCAL", None))
    debug = True

mongo_url = os.getenv("OSRS_MONGO_URI", "localhost:27017")
coll_name = os.getenv("OSRS_MONGO_COLL", "players")
playerdb = connect_mongo(mongo_url)[coll_name]

app = Dash(__name__,
           title="OSRS player clusters",
           external_stylesheets=[themes.BOOTSTRAP])
app = build_layout(app, appdata)
app = add_callbacks(app, appdata, playerdb)

app.run_server(debug=debug)
