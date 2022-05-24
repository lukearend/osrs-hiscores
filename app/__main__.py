#!/usr/bin/env python3

""" Entry point for main application. """

import os
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # uses deprecated version of dcc
    import dash_auth

from app import app
from app.root import root_layout
from src.common import connect_mongo


host = 'localhost'
if os.getenv('OSRS_ON_CLOUD', None):
    host = '0.0.0.0'  # serve to public internet

if not os.getenv('OSRS_DISABLE_AUTH', None):
    auth_coll = connect_mongo(url=os.environ['OSRS_MONGO_URI'], collection='auth')
    auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
    dash_auth.BasicAuth(app, username_password_list=auth_pairs)

debug = False if os.getenv('OSRS_DEBUG_OFF', None) else True

app.title = "OSRS hiscores explorer"
app.layout = root_layout()

app.run_server(host=host, debug=debug)
