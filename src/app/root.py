import warnings
from dataclasses import fields

import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from dash import Dash

from src.app.backend import Backend
from src.app.boxplot import Boxplot
from src.app.dropdowns import SplitMenu

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # uses deprecated version of dcc
    import dash_auth

from src.data.db import connect_mongo
from src.data.io import load_app_data


class MainApp:
    """ Dash application visualization clustering results. """

    def __init__(self, rootname: str, mongo_url: str, appdata_coll: str, appdata_file: str, auth: bool):
        """ Connect to data sources and build application components. """

        self.player_coll = connect_mongo(mongo_url, appdata_coll)
        self.app_data = load_app_data(appdata_file)

        theme = dbc.themes.DARKLY

        self.app = Dash(rootname, external_stylesheets=[theme])
        self.server = self.app.server
        self.run_server = self.app.run_server

        if auth:
            auth_coll = connect_mongo(mongo_url, 'auth')
            auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
            dash_auth.BasicAuth(self.app, username_password_list=auth_pairs)

        self.backend = Backend(self.app, self.app_data)
        self.datastore = self.backend.store

        init_split = list(self.app_data.keys())[0]
        self.splitmenu = SplitMenu(self.app, self.app_data, self.datastore, init_split=init_split)
        self.boxplot = Boxplot(self.app, self.app_data, self.datastore)

    def build_layout(self):
        """ Define global layout of components on the page. """

        storevars = []
        for field in fields(self.datastore):
            var = getattr(self.datastore, field.name)
            storevars.append(var)
        datastore = dbc.Col(storevars)

        splitmenu = dbc.Col(
            dbc.Row([
                dbc.Col(self.splitmenu.label),
                dbc.Col(self.splitmenu.dropdown),
            ], align='center'),
        )

        boxplot = dbc.Col([
            self.boxplot.title,
            self.boxplot.graph,
        ])

        self.app.layout = dbc.Container([
            dbc.Row(datastore),
            dbc.Row(splitmenu),
            dbc.Row(boxplot),
            dbc.Row(self.backend.view)
        ])

    def add_callbacks(self):
        """ Add dynamic behavior of application components. """

        self.backend.add_callbacks()
        self.splitmenu.add_callbacks()
        self.boxplot.add_callbacks()
