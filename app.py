#!/usr/bin/env python3

""" Entry point for main application. """

import os
import dash_auth
from app import app
from app.root import root_layout
from src.common import connect_mongo

if os.getenv('OSRS_USE_AUTH'):
    auth_coll = connect_mongo(url=os.environ['OSRS_MONGO_URI'], collection='auth')
    auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
    dash_auth.BasicAuth(app, username_password_list=auth_pairs)

debug = True if os.getenv('OSRS_DEBUG_ON') else False

app.title = "OSRS hiscores explorer"
app.layout = root_layout()

host = '0.0.0.0' if os.getenv('ON_HEROKU') else 'localhost'

server = app.server  # gunicorn finds and uses `server`
app.run_server(host=host, debug=debug, port=os.getenv('PORT'))
