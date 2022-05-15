from typing import OrderedDict

import dash_core_components as dcc
from dash import html

from src.data.types import SplitResults




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
