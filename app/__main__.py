#!/usr/bin/env python3

""" Visualize 3d-embedded cluster data with a Dash application. """

import os

from dash import Dash
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dash_bootstrap_components import themes

from app.layout import build_layout
from app.callbacks import add_callbacks

try:
    url = os.environ["MONGO_URI"]
except KeyError:
    raise ValueError("MONGO_URI is not set in environment")

client = MongoClient(url, serverSelectionTimeoutMS=10000)
db = client['osrs-hiscores']
try:
    db.command('ping')
except ServerSelectionTimeoutError:
    raise ValueError("could not connect to mongodb")
player_db = db['players']

app = Dash(__name__, external_stylesheets=[themes.BOOTSTRAP])
app = build_layout(app)
app = add_callbacks(app, player_db)

app.run_server(debug=True)
