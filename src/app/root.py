import warnings

import dash_bootstrap_components as dbc
from dash import Dash, html, dcc

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # uses deprecated version of dcc
    import dash_auth

from src.app import components, frontend, backend
from src.data.db import connect_mongo
from src.data.io import load_app_data


class MainApp:

    def __init__(self, rootname: str, mongo_url: str, appdata_coll: str, appdata_file: str, auth: bool):
        """ Initialize core app and connect to data sources. """

        self.player_coll = connect_mongo(mongo_url, appdata_coll)
        self.app_data = load_app_data(appdata_file)
        self.app = Dash(rootname)
        if auth:
            auth_coll = connect_mongo(mongo_url, 'auth')
            auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
            dash_auth.BasicAuth(self.app, username_password_list=auth_pairs)

        self.server = self.app.server
        self.run_server = self.app.run_server

    def init_layout(self):
        """ Build global layout of application page. """

        self.app.layout = dbc.Container([

            dcc.Store('controls:split'),
            dbc.Row([
                dbc.Col(html.Div("Choose split:"), className='label-text'),
                dbc.Col(components.splitmenu(self.app_data), className=''),
            ]),

            dcc.Store('boxplot:tickskills'),
            dcc.Store('boxplot:title:clusterid'),
            dcc.Store('boxplot:title:nplayers'),
            dbc.Row(
                dbc.Col([
                    components.boxplot_title(),
                    components.boxplot(),
                ]),
            ),
        ])

    def init_frontend(self):
        """ Attach callbacks for updating graphical elements. """

        self.app = frontend.add_boxplot(self.app)

    def init_backend(self):
        """ Attach callbacks for application logic and data processing. """

        self.app = backend.add_boxplot(self.app, self.app_data)
