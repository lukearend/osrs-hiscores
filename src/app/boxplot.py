from typing import OrderedDict, List

import dash_bootstrap_components as dbc
import numpy as np
from dash import Dash, Input, Output, html, dcc, no_update
from plotly import graph_objects as go

from src.app import colors
from src.app import styles
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
        @self.app.callback(
            Output(self.graph, 'figure'),
            Input(self.store.currentsplit, 'data'),
        )
        def make_boxplot(split: str) -> go.Figure():
            if split is None:
                return no_update

            skills = self.app_data[split].skills
            hidden = np.full(len(skills), -100)
            boxtrace = go.Box(lowerfence=hidden, upperfence=hidden,
                              median=hidden, q1=hidden, q3=hidden)

            imsize = 10  # icon container size in y-axis units
            imscale = 0.75  # icon size as a proportion of container
            padabove = 3  # padding above level 99 in y-axis units
            yticks = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]

            padbelow = (1 - imscale) * imsize
            yaxis = dict(
                range=(1 - 2 * padbelow - imscale * imsize, 99 + padabove),
                fixedrange=True,  # not zoomable
                zeroline=False,
                tickvals=yticks,
            )
            xaxis = dict(
                range=(-0.5, len(skills) - 0.5),
                fixedrange=True,  # not zoomable
                tickvals=[],  # these ticks are drawn on as images instead
            )
            margin = dict(b=0, t=0)
            # layout_margin = dict(b=20, l=2, r=0, t=0),  # left margin adds space for y tick numbers

            fig = go.Figure(data=boxtrace)
            fig.update_layout(dict(
                xaxis=xaxis,
                yaxis=yaxis,
                margin=margin,
                paper_bgcolor=colors.BOXPLOT_PAPER,
                plot_bgcolor=colors.BOXPLOT_BG,
                yaxis_tickfont_size=styles.BOXPLOT_AXIS_FONTSIZE,
            ))
            fig.update_traces(
                marker=dict(color=colors.BOXPLOT_TRACE),
            )
            for i, skill in enumerate(skills):
                fig.add_layout_image(
                    source='data:image/png;base64,' + load_icon_b64(skill),
                    layer='above',
                    xanchor='center',  # center image horizontally on xtick
                    yanchor='top',  # dangle image below horizontal baseline
                    xref='x',  # x offset in x-axis units
                    yref='y',  # y offset in y-axis units
                    x=i,
                    y=1 - padbelow,
                    sizex=imscale,
                    sizey=imscale * imsize,
                )
            return fig

        @self.app.callback(
            Output(self.title, 'children'),
            Input(self.store.boxplot_clusterid, 'data'),
            Input(self.store.boxplot_nplayers, 'data'),
        )
        def update_boxplot_title(clusterid: int, nplayers: int) -> List[html.Span]:
            if clusterid is None or nplayers is None:
                part1, part2 = "Cluster stats", None
            else:
                part1, part2 = f"Cluster {clusterid} stats", f" ({nplayers} players)"

            part1 = html.Span(part1)
            part2 = html.Span(part2, className='boxplot-title-parens')
            return [part1, part2]
