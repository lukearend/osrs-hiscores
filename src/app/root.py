import warnings
from dataclasses import fields

import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from dash import Dash

from src.app.backend import Backend
from src.app.boxplot import Boxplot
from src.app.dropdowns import SplitMenu, PointSizeMenu
from src.app.input import UsernameInput

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
        load_figure_template('darkly')

        self.app = Dash(rootname, external_stylesheets=[theme])
        self.server = self.app.server
        self.run_server = self.app.run_server

        if auth:
            auth_coll = connect_mongo(mongo_url, 'auth')
            auth_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
            dash_auth.BasicAuth(self.app, username_password_list=auth_pairs)

        self.backend = Backend(self.app, self.app_data)
        self.datastore = self.backend.store

        self.uname_input = UsernameInput(self.app, self.app_data, self.datastore)
        self.split_menu = SplitMenu(self.app, self.app_data, self.datastore)
        self.ptsize_menu = PointSizeMenu(self.app, self.app_data, self.datastore)
        self.boxplot = Boxplot(self.app, self.app_data, self.datastore)

    def build_layout(self):
        """ Define global layout of components on the page. """

        storevars = []
        for field in fields(self.datastore):
            var = getattr(self.datastore, field.name)
            storevars.append(var)

        uname_input = dbc.Row([
                dbc.Col(self.uname_input.label, width='auto'),
                dbc.Col(self.uname_input.input),
            ],
            align='center',
        )
        split_menu = dbc.Row([
                dbc.Col(self.split_menu.label, width='auto'),
                dbc.Col(self.split_menu.dropdown),
            ],
            align='center',
        )
        ptsize_menu = dbc.Row([
                dbc.Col(self.ptsize_menu.label, width='auto'),
                dbc.Col(self.ptsize_menu.dropdown),
            ],
            align='center',
        )
        controls = dbc.Row(
            [
                dbc.Col(split_menu, width='auto'),
                dbc.Col(ptsize_menu),
            ],
            align='center',
        )
        boxplot = dbc.Col([
            self.boxplot.title,
            self.boxplot.graph,
        ])

        self.app.layout = dbc.Container([
            dbc.Row(dbc.Col(storevars)),
            dbc.Row(dbc.Col(uname_input)),
            dbc.Row(dbc.Col(controls)),
            dbc.Row(dbc.Col(boxplot)),
            dbc.Row(self.backend.view)
        ])

    def add_callbacks(self):
        """ Add dynamic behavior of application components. """

        self.backend.add_callbacks()
        self.uname_input.add_callbacks()
        self.split_menu.add_callbacks()
        self.ptsize_menu.add_callbacks()
        self.boxplot.add_callbacks()
