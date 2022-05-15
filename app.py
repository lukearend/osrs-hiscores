#!/usr/bin/env python3

""" Entry point for main application. """

import os
from src.app.root import MainApp

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

app = MainApp(__name__, mongo_url, appdata_coll, appdata_file, auth)
app.init_layout()
app.init_frontend()
app.init_backend()

server = app.server  # gunicorn looks for 'server' in global namespace

if __name__ == '__main__':
    host = "0.0.0.0" if os.getenv('ON_HEROKU', False) else 'localhost'
    app.run_server(debug=debug, host=host, port=os.getenv('PORT', 8050))
