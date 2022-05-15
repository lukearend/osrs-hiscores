import warnings

import dash_bootstrap_components as dbc
from dash import Dash, html, dcc

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # uses deprecated version of dcc
    import dash_auth

from src.app.dropdowns import SplitMenu
from src.data.db import connect_mongo
from src.data.io import load_app_data


class MainApp:

    def __init__(self, rootname: str, mongo_url: str, appdata_coll: str, appdata_file: str, auth: bool):
        """ Connect to data sources and build application components. """

        self.player_coll = connect_mongo(mongo_url, appdata_coll)
        self.app_data = load_app_data(appdata_file)
        self.app = Dash(rootname)
        if auth:
            auth_coll = connect_mongo(mongo_url, 'auth')
            auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
            dash_auth.BasicAuth(self.app, username_password_list=auth_pairs)

        self.server = self.app.server
        self.run_server = self.app.run_server

        init_split = list(self.app_data.keys())[0]
        self.splitmenu = SplitMenu(self.app, self.app_data, init_split)

    def build_layout(self):
        """ Define global layout of components on the page. """

        self.app.layout = dbc.Container([

            dbc.Col(
                dbc.Row([
                    dbc.Col(self.splitmenu.label),
                    dbc.Col(self.splitmenu.dropdown),
                ]),
            ),

        ], className='app')

    def add_callbacks(self):
        """ Attach callbacks for dynamic/interactive elements. """
