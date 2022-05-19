import collections
from dataclasses import dataclass
from typing import OrderedDict

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, html, callback_context, no_update, dcc

from src.app.backend import DataStore
from src.data.types import SplitResults


@dataclass
class MenuItem:
    label: str
    button: dbc.DropdownMenuItem


class DropdownMenu:
    """ General-purpose dropdown menu. """

    def __init__(self, app: Dash, storevar: dcc.Store, optlabels: OrderedDict[str, str], name: str):
        self.app = app
        self.storevar = storevar
        self.optlabels = optlabels
        self.name = name

        self.menuitems = collections.OrderedDict()
        for val, label in self.optlabels.items():
            button = dbc.DropdownMenuItem(label, id=f'{name}:item:{val}')
            item = MenuItem(label=label, button=button)
            self.menuitems[val] = item

        self.component = dbc.DropdownMenu(
            [item.button for item in self.menuitems.values()],
            label='',
            id=name,
            menu_variant='dark',
        )

    def add_callbacks(self):

        @self.app.callback(
            Output(self.component, 'label'),
            Input(self.storevar, 'data'),
        )
        def update_button_text(newval: str) -> str:
            return self.menuitems[newval].label

        @self.app.callback(
            Output(self.storevar, 'data'),
            *[Input(item.button, 'n_clicks')
              for item in self.menuitems.values()],
        )
        def select_menu_item(*args) -> str:
            ctx = callback_context
            if not ctx.triggered:
                optvals = list(self.optlabels.keys())
                return optvals[0]
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            newval = button_id.split(':')[2]
            return newval


class SplitMenu:
    """ Dropdown menu for selecting the current split. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults], datastore: DataStore):
        self.app = app
        self.app_data = app_data
        self.store = datastore

        optlabels = collections.OrderedDict()
        for split in self.app_data.keys():
            optlabels[split] = {
                'all': "All skills",
                'cb': "Combat skills only",
                'noncb': "Non-combat skills only",
            }[split]

        dropdown = DropdownMenu(
            app=self.app,
            storevar=self.store.currentsplit,
            optlabels=optlabels,
            name='splitmenu',
        )

        self.label = html.Div("Choose split:", className='label-text')
        self.dropdown = dropdown.component
        self.add_callbacks = dropdown.add_callbacks


class PointSizeMenu:
    """ Dropdown menu for setting the scatterplot point size. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults],
                 datastore: DataStore):

        self.app = app
        self.app_data = app_data
        self.store = datastore

        opts = ['small', 'medium', 'large']
        optlabels = collections.OrderedDict([(opt, opt) for opt in opts])

        dropdown = DropdownMenu(
            app=self.app,
            storevar=self.store.scatterplot_ptsize,
            optlabels=optlabels,
            name='ptsizemenu'
        )

        self.label = html.Div("Point size:", className='label-text')
        self.dropdown = dropdown.component
        self.add_callbacks = dropdown.add_callbacks
