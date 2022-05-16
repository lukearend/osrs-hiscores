import collections
from dataclasses import dataclass
from typing import OrderedDict

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, html, dcc, callback_context

from src.app.store import SplitMenuState
from src.data.types import SplitResults


@dataclass
class MenuItem:
    label: str
    button: dbc.DropdownMenuItem


class SplitMenu:
    """ Dropdown menu for selecting the current split. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults], init_split: str):
        self.app = app
        self.app_data = app_data
        self.init_split = init_split
        self.state = SplitMenuState(
            split=dcc.Store('splitmenu:split')
        )

        splits = self.app_data.keys()
        opttext = {
            'all': "All skills",
            'cb': "Combat skills only",
            'noncb': "Non-combat skills only",
        }

        self.menuitems = collections.OrderedDict()
        for split in splits:
            label = opttext[split]
            button = dbc.DropdownMenuItem(label, id=f'splitmenu:item:{split}', className='dropdown-item')
            item = MenuItem(label=label, button=button)
            self.menuitems[split] = item

        self.label = html.Div("Choose split:", className='label-text')
        self.dropdown = dbc.DropdownMenu(
            [item.button for item in self.menuitems.values()],
            label=None,
            id='splitmenu',
        )

    def add_callbacks(self):

        @self.app.callback(
            Output(self.dropdown, 'label'),
            Input(self.state.split, 'data'),
        )
        def update_button_text(newsplit: str) -> str:
            return self.menuitems[newsplit].label

        @self.app.callback(
            Output(self.state.split, 'data'),
            *[
                Input(item.button, 'n_clicks')
                for item in self.menuitems.values()
            ],
        )
        def select_menu_item(*args) -> str:
            ctx = callback_context

            if not ctx.triggered:
                return self.init_split

            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            newsplit = button_id.split(':')[2]
            return newsplit
