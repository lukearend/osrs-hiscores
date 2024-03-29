import os
from typing import Dict

import dash_auth
from dash import Dash
from dash_bootstrap_components import themes
from dash_bootstrap_templates import load_figure_template

from src.analysis.appdata import SplitResults
from src.common import connect_mongo
from app.helpers import load_app_data

if os.getenv("OSRS_APPDATA_URI") is None:
    raise ValueError("missing config variable: OSRS_APPDATA_URI")
if os.getenv("OSRS_MONGO_URI") is None:
    raise ValueError("missing config variable: OSRS_MONGO_URI")
if os.getenv("OSRS_MONGO_COLL") is None:
    raise ValueError("missing config variable: OSRS_MONGO_COLL")

load_figure_template('darkly')

app = Dash(
    __name__,
    external_stylesheets=[themes.DARKLY],
    meta_tags=[{  # tell mobile browser that app has been optimized for mobile
        'name': 'viewport',
        'content': 'width=device-width, initial-scale=1',
    }],
)
appdb = connect_mongo(os.environ['OSRS_MONGO_URI'], os.environ['OSRS_MONGO_COLL'])
appdata: Dict[str, SplitResults] = load_app_data(os.environ['OSRS_APPDATA_URI'])

if os.getenv('OSRS_USE_AUTH'):
    auth_coll = connect_mongo(os.environ['OSRS_MONGO_URI'], collection='auth')
    auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
    dash_auth.BasicAuth(app, username_password_list=auth_pairs)
