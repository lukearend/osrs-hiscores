import os

from dash import Dash
from dash_bootstrap_components import themes
from dash_bootstrap_templates import load_figure_template

from src.common import connect_mongo
from app.helpers import load_app_data

if os.getenv("OSRS_MONGO_URI") is None:
    raise ValueError("missing config variable: OSRS_MONGO_URI")
if os.getenv("OSRS_APPDATA_URI") is None:
    raise ValueError("missing config variable: OSRS_APPDATA_URI")

load_figure_template('darkly')
app = Dash(__name__, external_stylesheets=[themes.DARKLY])
appdb = connect_mongo(os.environ['OSRS_MONGO_URI'], 'players')
appdata = load_app_data(os.environ['OSRS_APPDATA_URI'])
server = app.server  # gunicorn finds and uses `server` in root namespace
