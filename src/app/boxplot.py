from typing import OrderedDict, List

import numpy as np
from dash import Dash, Input, Output, html, dcc, no_update
from plotly import graph_objects as go

from src.app import colors
from src.app.backend import DataStore
from src.app.helpers import load_icon_b64
from src.data.types import SplitResults


class Boxplot:
    """ Boxplot displaying quartiles for the hovered cluster. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults], datastore: DataStore):
        self.app = app
        self.app_data = app_data
        self.store = datastore

        self.title = html.Div(
            children='',
            id='boxplot-title',
            className='label-text',
        )
        self.graph = dcc.Graph(
            figure={},  # Dash bug: figure must be explicitly initialized to an empty value
            config={'displayModeBar': False},  # hide plotly toolbar
            id='boxplot',
            className='boxplot',
        )

    def add_callbacks(self):
        # @self.app.callback(
        #     Output(self.graph, 'figure'),
        #     Input(self.store.currentsplit, 'data'),
        #     prevent_initial_call=True,
        # )
        # def make_boxplot(split: str) -> go.Figure():
        #     if split is None:
        #         return no_update
        #
        #     skills = self.app_data[split].skills
        #     nan = np.full(len(skills), np.nan)
        #     boxtrace = go.Box(lowerfence=nan, upperfence=nan, median=nan, q1=nan, q3=nan)
        #
        #     yticks = [1, 20, 40, 60, 80, 99]
        #     padbelow = 3  # space below level 1 on plot
        #     padabove = 5  # space above level 99 on plot
        #     yaxis = dict(
        #         range=(1 - padbelow, 99 + padabove),
        #         fixedrange=True,  # not zoomable
        #         tickvals=yticks,
        #     )
        #     xaxis = dict(
        #         range=(-0.5, len(skills) - 0.5),
        #         fixedrange=True,  # not zoomable
        #         tickvals=[],  # these ticks are drawn on as images instead
        #     )
        #
        #     fig = go.Figure(data=boxtrace)
        #     fig.update_layout(dict(
        #         xaxis=xaxis,
        #         yaxis=yaxis,
        #         paper_bgcolor=colors.BOXPLOT_PAPER,
        #         plot_bgcolor=colors.BOXPLOT_BG,
        #     ))
        #     fig.update_traces(
        #         marker=dict(color=colors.BOXPLOT_TRACE),
        #     )
        #     for i, skill in enumerate(skills):
        #         fig.add_layout_image(
        #             source='data:image/png;base64,' + load_icon_b64(skill),
        #             layer='above',
        #             xanchor='center',  # center image horizontally on xtick
        #             yanchor='top',  # dangle image below horizontal baseline
        #             xref='x',  # x offset units: boxplot x-coordinate
        #             yref='y',  # y offset units: boxplot y-coordinate
        #             x=i,
        #             y=padbelow,
        #         )

        @self.app.callback(
            Output(self.title, 'children'),
            Input(self.store.boxplot_clusterid, 'data'),
            Input(self.store.boxplot_nplayers, 'data'),
        )
        def update_boxplot_title(clusterid: int, nplayers: int) -> List[html.Span]:
            if clusterid is None or nplayers is None:
                part1, part2 = "Cluster level ranges", None
            else:
                part1, part2 = f"Cluster {clusterid} level ranges", f" ({nplayers} players"

            bold = html.Span(part1)
            norm = html.Span(part2, className='rs-regular')
            return [bold, norm]