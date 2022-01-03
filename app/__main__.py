#!/usr/bin/env python3

""" Visualize 3d-embedded cluster data with a Dash application. """

import pathlib
import pickle
import sys

from dash import Dash
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dash_bootstrap_components import themes

from app.layout import build_layout
from app.callbacks import add_callbacks


url = 'localhost:{}'.format(sys.argv[1])
client = MongoClient(url, serverSelectionTimeoutMS=10000)
db = client['osrs-hiscores']
try:
    db.command('ping')
except ServerSelectionTimeoutError:
    raise ValueError("could not connect to mongodb")
player_db = db['players']

data_file = pathlib.Path(__file__).resolve().parent / 'assets/app_data.pkl'
with open(data_file, 'rb') as f:
    app_data = pickle.load(f)

app = Dash(__name__, external_stylesheets=[themes.BOOTSTRAP])
app = build_layout(app, app_data)
app = add_callbacks(app, app_data, player_db)

app.run_server(debug=True)
