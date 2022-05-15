from typing import OrderedDict

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, html, dcc

from src.data.types import SplitResults


class SplitMenu:
    """ Dropdown menu for selecting the current split. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults], init_val: str) -> dbc.Row:
        self.app = app
        self.app_data = app_data

        splits = list(self.app_data.keys())
        optlabels = {
            'all': "All skills",
            'cb': "Combat skills only",
            'noncb': "Non-combat skills only",
        }
        opts = [{'label': optlabels[split], 'value': split} for split in splits]

        self.label = html.Div("Choose split:", className='label-text')
        self.dropdown = dcc.Dropdown(
            value=init_val,
            options=opts,
            clearable=False,
            id='split-menu',
            className='dropdown'
        )
