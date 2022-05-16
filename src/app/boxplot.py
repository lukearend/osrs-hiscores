from typing import OrderedDict

import dash_core_components as dcc
import numpy as np
from dash import Dash, Input, Output, html, callback_context
from plotly import graph_objects as go

from src.app import colors
from src.app.helpers import load_icon_b64
from src.app.store import BoxplotState, SplitMenuState, BackendState
from src.data.types import SplitResults


class Boxplot:
    """ Boxplot displaying quartiles for the hovered cluster. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults], backend: BackendState):

        self.app = app
        self.app_data = app_data
        self.backend = backend
        self.state = BoxplotState(
            clusterid=dcc.Store('boxplot:clusterid'),
            nplayers=dcc.Store('boxplot:nplayers'),
        )

        self.title = html.Div(
            children=None,
            id='boxplot-title',
        )
        self.graph = dcc.Graph(
            figure=None,
            config={'displayModeBar': False},  # hide plotly toolbar
            id='boxplot',
        )

    def add_callbacks(self):

        @self.app.callback(
            Output(self.graph, 'figure'),
            Input(self.backend.currentsplit, 'data'),
        )
        def make_boxplot(split: str) -> go.Figure():
            skills = self.app_data[split].skills
            nan = np.full(len(skills), np.nan)
            boxtrace = go.Box(lowerfence=nan, upperfence=nan, median=nan, q1=nan, q3=nan)

            yticks = [1, 20, 40, 60, 80, 99]
            padbelow = 3  # space below level 1 on plot
            padabove = 5  # space above level 99 on plot
            yaxis = dict(
                range=(1 - padbelow, 99 + padabove),
                fixedrange=True,  # not zoomable
                tickvals=yticks,
            )
            xaxis = dict(
                range=(-0.5, len(skills) - 0.5),
                fixedrange=True,  # not zoomable
                tickvals=[],  # will be drawn on as images instead

            )

            fig = go.Figure(
                data=boxtrace,
                layout=dict(
                    xaxis=xaxis,
                    yaxis=yaxis,
                    paper_bgcolor=colors.BOXPLOT_PAPER,
                    plot_bgcolor=colors.BOXPLOT_BG,
                    marker=dict(color=colors.BOXPLOT_TRACE),
                ),
            )

            for i, skill in enumerate(skills):
                imgb64 = load_icon_b64(skill)
                fig.add_layout_image(
                    source='data:image/png;base64,' + imgb64,
                    layer='above',
                    xanchor='center',  # center image horizontally on xtick
                    yanchor='top',  # dangle image below horizontal baseline
                    xref='x',  # x offset units: boxplot x-coordinate
                    yref='y',  # y offset units: boxplot y-coordinate
                    x=i,
                    y=padbelow,
                )

        @self.app.callback(
            Output(self.title, 'children'),
            Input(self.state.clusterid, 'data'),
            Input(self.state.nplayers, 'data'),
        )
        def update_boxplot_title(clusterid: int, nplayers: int) -> html.Div:
            print(callback_context)

            if clusterid is None or nplayers is None:
                part1, part2 = "Cluster level ranges", None
            else:
                part1, part2 = f"Cluster {clusterid} level ranges", f" ({nplayers} players"

            part1 = html.Span(part1)
            part2 = html.Span(part2, className='rs-regular')
            return html.Div(part1, part2, className='label-text')
