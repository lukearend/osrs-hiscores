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
playerdb = db['players']

datapath = pathlib.Path(__file__).resolve().parent / 'assets/appdata.pkl'
with open(datapath, 'rb') as f:
    appdata = pickle.load(f)

app = Dash(__name__, external_stylesheets=[themes.BOOTSTRAP])
app = build_layout(app, appdata)
app = add_callbacks(app, appdata, playerdb)

app.run_server(debug=True)
