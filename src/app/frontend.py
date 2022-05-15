from typing import List

import numpy as np
from dash import Dash, Input, Output, html
from plotly import graph_objects as go

from src.app import colors
from src.app.helpers import load_icon_b64


def add_controls(app: Dash) -> Dash:

    @app.callback(
        Output('controls:split', 'data'),
        Input('split-menu', 'value'),
    )
    def set_current_split(newsplit):
        return newsplit


def add_boxplot(app: Dash) -> Dash:

    @app.callback(
        Output('boxplot', 'figure'),
        Input('boxplot:tickskills', 'data'),
    )
    def render_empty_boxplot(skills: List[int]) -> go.Figure():
        nan = np.full(len(skills), np.nan)
        box = go.Box(lowerfence=nan, upperfence=nan, median=nan, q1=nan, q3=nan)

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
            data=box,
            layout=dict(
                xaxis=xaxis,
                yaxis=yaxis,
                font='rs-regular',
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

    @app.callback(
        Output('boxplot-title', 'children'),
        Input('boxplot:title:clusterid', 'data'),
        Input('boxplot:title:nplayers', 'data'),
    )
    def render_boxplot_title(clusterid: int, nplayers: int) -> html.Div:
        if clusterid is None or nplayers is None:
            part1, part2 = "Cluster level ranges", None
        else:
            part1, part2 = f"Cluster {clusterid} level ranges", f" ({nplayers} players"

        part1 = html.Span(part1)
        part2 = html.Span(part2, className='rs-regular')
        return html.Div(part1, part2, className='label-text')

    return app
