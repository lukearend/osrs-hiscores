#!/usr/bin/env python3

""" Visualize 3d-embedded cluster data with a Dash application. """

import pickle
import sys

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app.layout import build_layout


db = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5)['osrs-hiscores']
player_collection = db['players']
try:
    db.command('ping')
except ServerSelectionTimeoutError:
    raise ValueError("could not connect to mongodb")

with open(sys.argv[1], 'rb') as f:
    appdata = pickle.load(f)

mainapp = build_layout(appdata)
mainapp = attach_callbacks(mainapp, appdata)

main.run_server(debug=True)
