from typing import Dict

import numpy as np
from dash import Input, Output, html, dcc, no_update
from plotly import graph_objects as go

from app import app, appdata, styles
from app.helpers import load_icon_b64


def boxplot_title():
    return html.Div(
        id='boxplot-title',
        children='',
        className='label-text',
    )


def boxplot():
    return dcc.Graph(
        id='boxplot',
        figure={},  # figure must be explicitly initialized to an empty value (Dash bug)
        config={'displayModeBar': False},
        className='boxplot-graph',
    )


@app.callback(
    Output('boxplot', 'figure'),
    Input('current-split', 'data'),
)
def redraw_boxplot(split: str) -> go.Figure():
    if split is None:
        return no_update

    skills = appdata[split].skills
    hidden = np.full(len(skills), -100)
    boxtrace = go.Box(lowerfence=hidden, upperfence=hidden,
                      median=hidden, q1=hidden, q3=hidden)

    imsize = 10     # icon container size in y-axis units
    imscale = 0.75  # icon size as a proportion of container
    padabove = 3    # padding above level 99 in y-axis units
    yticks = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]

    padbelow = (1 - imscale) * imsize
    yaxis = dict(
        range=(1 - 2 * padbelow - imscale * imsize, 99 + padabove),
        fixedrange=True,
        zeroline=False,
        tickvals=yticks,
        tickfont={'family': 'sans-serif'},
    )
    xaxis = dict(
        range=(-0.5, len(skills) - 0.5),
        fixedrange=True,
        tickvals=[],  # these ticks are drawn on as images instead
    )
    margin = dict(b=0, t=0)

    fig = go.Figure(data=boxtrace)
    fig.update_layout(dict(
        xaxis=xaxis,
        yaxis=yaxis,
        margin=margin,
        paper_bgcolor=styles.BOXPLOT_PAPER,
        plot_bgcolor=styles.BOXPLOT_BG,
        yaxis_tickfont_size=styles.BOXPLOT_AXIS_FONTSIZE,
    ))
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

@app.callback(
    Output('boxplot-title', 'children'),
    Input('boxplot-title-data', 'data'),
)
def update_boxplot_title(data: Dict[str, int]) -> html.Div:
    if data is None:
        return html.Strong("Cluster stats")

    clusterid = data['cluster_id']
    nplayers = data['cluster_size']
    bold = html.Strong(f"Cluster {clusterid} stats")
    normal = f" ({nplayers} players)"
    return html.Div([bold, normal])
