from dataclasses import fields, asdict
import warnings

import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from dash import Dash

from src.app.backend import Backend
from src.app.store import FrontendState

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # uses deprecated version of dcc
    import dash_auth

from src.app.dropdowns import SplitMenu
from src.app.boxplot import Boxplot
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

        init_split = list(self.app_data.keys())[0]
        self.splitmenu = SplitMenu(self.app, self.app_data, init_split=init_split)

        self.boxplot = Boxplot(self.app, self.app_data, self.backend.state)

        self.frontend = FrontendState(
            splitmenu=self.splitmenu.state,
            boxplot=self.boxplot.state,
        )

        self.backend = Backend(self.app, self.app_data, self.frontend)

    def build_layout(self):
        """ Define global layout of components on the page. """

        statevars = []
        for field in fields(self.backend.state):
            value = getattr(self.backend.state, field.name)
            statevars.append(value)
        for component in fields(self.frontend):
            state = getattr(self.frontend, component.name)
            for statevar, value in asdict(state).items():
                statevars.append(value)
        statevars = dbc.Col(statevars)

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
            dbc.Row(statevars),
            dbc.Row(splitmenu),
            dbc.Row(boxplot),
        ])

    def add_callbacks(self):
        """ Attach callbacks for dynamic/interactive elements. """

        self.splitmenu.add_callbacks()
        self.boxplot.add_callbacks()
        self.backend.add_callbacks()
