from typing import OrderedDict

import dash_core_components as dcc
from dash import html

from src.data.types import SplitResults

def splitmenu(app_data: OrderedDict[str, SplitResults]) -> dcc.Dropdown:
    """ Dropdown menu for selecting the current split. """

    splits = list(app_data.keys())
    labels = {
        'all': "All skills",
        'cb': "Combat skills only",
        'noncb': "Non-combat skills only",
    }
    splitopts = [{'label': labels[split], 'value': split} for split in splits]
    initsplit = splits[0]
    return dcc.Dropdown(
        value=initsplit,
        options=splitopts,
        clearable=False,
        id='split-menu',
    )

def boxplot() -> dcc.Graph:
    """ Boxplot which displays quartiles for the hovered cluster. """

    return dcc.Graph(
        figure=None,
        config={'displayModeBar': False},  # hide plotly toolbar
        id='boxplot',
    )

def boxplot_title() -> html.Div:
    """ Boxplot title updates with the hovered cluster. """

    return html.Div(
        children=None,
        id='boxplot-title',
    )
