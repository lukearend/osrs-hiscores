#!/usr/bin/env python3

""" Entry point for main application. """

import os
from src.app import mainapp

mongo_url = os.getenv("OSRS_MONGO_URI", None)
appdata_coll = os.getenv("OSRS_APPDATA_COLL", None)
appdata_file = os.getenv("OSRS_APPDATA_FILE", None)
auth = os.getenv("OSRS_REQUIRE_AUTH", 'false')
debug = os.getenv("OSRS_DEBUG_MODE", 'true')

if mongo_url is None:
    raise ValueError("missing config variable: OSRS_MONGO_URI")
if appdata_coll is None:
    raise ValueError("missing config variable: OSRS_APPDATA_COLL")
if appdata_file is None:
    raise ValueError("missing config variable: OSRS_APPDATA_FILE")

auth = False if auth == 'false' else bool(auth)
debug = False if debug == 'false' else bool(debug)

app = mainapp(mongo_url, appdata_coll, appdata_file, auth)

server = app.server
app.run_server(debug=debug)
