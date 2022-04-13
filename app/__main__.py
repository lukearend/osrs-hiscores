#!/usr/bin/env python3

""" A Dash application to visualize the results of clustering the OSRS hiscores. """

import os

from app.layout import build_layout
from app.callbacks import add_callbacks
from src.analysis.app import connect_mongo

db = connect_mongo(url=os.getenv("OSRS_MONGO_URI", "localhost:27017"))
app = build_layout()
add_callbacks(app, db)
app.run_server(debug=True)
