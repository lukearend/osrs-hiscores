#!/usr/bin/env python3

""" A Dash application to visualize the results of clustering the OSRS hiscores. """

import os

from dash import Dash
from dash_bootstrap_components import themes

from src import env_var, connect_mongo
from src.app import load_appdata_local, load_appdata_s3
from src.app.layout import build_layout
from src.app.callbacks import add_callbacks

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
coll = connect_mongo(mongo_url)[coll_name]

app = Dash(__name__,
           title="OSRS player clusters",
           external_stylesheets=[themes.BOOTSTRAP])
app = build_layout(app, appdata)
app = add_callbacks(app, appdata, coll)

app.run_server(debug=debug)
