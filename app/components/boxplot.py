from typing import Dict, Any, List

import numpy as np
from dash import State, Input, Output, html, dcc, no_update
from plotly import graph_objects as go

from app import app, styles
from app.helpers import load_icon_b64, load_boxplot_layout


def boxplot_title():
    return html.Div(id='boxplot-title')


def boxplot():
    return dcc.Graph(
        id='boxplot',
        figure={},  # figure must be explicitly initialized to an empty value (Dash bug) todo: still true?
        config={'displayModeBar': False},
        className='boxplot-graph',
        style={
            'height': styles.BOXPLOT_HEIGHT,
        }
    )


@app.callback(
    Output('boxplot', 'extendData'),
    Input('boxplot-data', 'data'),
    State('current-split', 'data'),
)
def update_boxplot_trace(data_dict: Dict[str, Any], split: str):
    if data_dict is None:
        return no_update

    skills = load_boxplot_layout()[split]
    boxdata = []
    for i, p in enumerate([0, 25, 50, 75, 100]):
        lvls_dict = data_dict['quartiles'][i]
        skill_lvls = [lvls_dict[skill] for skill in skills]
        boxdata.append(skill_lvls)

    q0, q1, q2, q3, q4 = np.array(boxdata)
    iqr = q3 - q1
    traces = {
        'lowerfence': np.maximum(q1 - 1.5 * iqr, q0),
        'q1': q1,
        'median': q2,
        'q3': q3,
        'upperfence': np.minimum(q3 + 1.5 * iqr, q4),
    }
    traces = {t: d.astype('int') for t, d in traces.items()}

    extendtraces = {name: [data] for name, data in traces.items()}
    extendinds = [0]
    maxpts = len(skills)
    return [extendtraces, extendinds, maxpts]


@app.callback(
    Output('boxplot', 'figure'),
    Input('current-split', 'data'),
)
def redraw_boxplot(split: str) -> go.Figure:
    if split is None:
        return no_update

    skills = load_boxplot_layout()[split]
    hidden = np.full(len(skills), -100)
    boxtrace = go.Box(lowerfence=hidden, upperfence=hidden,
                      median=hidden, q1=hidden, q3=hidden)

    imsize = 10     # icon container size in y-axis units
    imscale = 0.85  # icon size as a proportion of container
    padabove = 5    # padding above level 99 in y-axis units
    yticks = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]

    padbelow = (1 - imscale) * imsize
    yaxis = dict(
        range=(1 - 2 * padbelow - imscale * imsize, 99 + padabove),
        fixedrange=True,
        zeroline=False,
        tickvals=yticks,
    )
    xaxis = dict(
        range=(-0.5, len(skills) - 0.5),
        fixedrange=True,
        tickvals=[],  # these ticks are drawn on as images instead
    )
    margin = dict(b=0, t=0)

    fig = go.Figure(data=boxtrace)
    fig.update_layout(dict(
        hovermode=False,
        xaxis=xaxis,
        yaxis=yaxis,
        margin=margin,
        paper_bgcolor=styles.BG_COLOR,
        plot_bgcolor=styles.BOXPLOT_BG_COLOR,
        yaxis_tickfont_family='OSRS Chat',
    ))
    for i, skill in enumerate(skills):
        fig.add_layout_image(
            source='data:image/png;base64,' + load_icon_b64(skill),
            layer='above',
            xanchor='center',  # center image horizontally on xtick
            yanchor='top',     # dangle image below horizontal baseline
            xref='x',          # x offset in x-axis units
            yref='y',          # y offset in y-axis units
            x=i,
            y=1 - padbelow,
            sizex=imscale,
            sizey=imscale * imsize,
        )
    return fig

@app.callback(
    Output('boxplot-title', 'children'),
    Input('boxplot-data', 'data'),
)
def update_boxplot_title(data: Dict[str, Any]) -> html.Div:
    if data is None:
        return html.Strong("Cluster stats")

    clusterid = data['id']
    nplayers = data['num_players']
    bold = html.Strong(f"Cluster {clusterid} stats")
    normal = f" ({nplayers} players)"
    return html.Div([bold, normal])
