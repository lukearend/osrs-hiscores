from typing import Dict, Any

import dash_core_components as dcc
import numpy as np
from plotly import graph_objects as go
from dash import Output, Input, no_update

from app import app, styles
from app.styles import PLAYER_COLOR_SEQ as uname_colors


def scatterplot():
    return dcc.Graph(
        id='scatterplot',
        figure={},
        className='scatterplot-graph',
        style={
            'height': styles.SCATTERPLOT_HEIGHT,
        }
    )


# @app.callback(
#     Output('scatterplot', 'extendData'),
#     Input('scatterplot-data', 'data'),
# )
# def update_scatterplot_traces(data_dict: Dict[str, Any]):
#     if not data_dict:
#         return no_update
#
#     traces = {
#         'x': data_dict['cluster_x'],
#         'y': data_dict['cluster_y'],
#         'z': data_dict['cluster_z'],
#     }
#
#     extendtraces = {name: [data] for name, data in traces.items()}
#     extendinds = [0]
#     maxpts = len(traces['x'])
#     return [extendtraces, extendinds, maxpts]


def ptsize_fn(x):
    x = np.clip(x, 1, styles.SCATTERPLOT_PTSIZE_MAX_NPLAYERS)
    x = np.sqrt(x) * styles.SCATTERPLOT_PTSIZE_CONSTANT
    return x


@app.callback(
    Output('scatterplot', 'figure'),
    Input('scatterplot-data', 'data'),
    Input('point-size', 'data'),
)
def redraw_scatterplot(data_dict: Dict[str, Any], ptsize: int) -> go.Figure:
    if not data_dict:
        return no_update

    fig = go.Figure()

    nplayers = data_dict['cluster_nplayers']
    size_factor = {
        'small': 1,
        'medium': 2,
        'large': 3,
    }[ptsize]
    ptsizes = ptsize_fn(nplayers) * size_factor

    clustertrace = go.Scatter3d(
        x=data_dict['cluster_x'],
        y=data_dict['cluster_y'],
        z=data_dict['cluster_z'],
        mode='markers',
        marker=dict(
            size=ptsizes,
            color=styles.SCATTERPLOT_PTS_COLOR,
        ),
    )
    fig.add_trace(clustertrace)

    # tracelen = len(data_dict['usernames'])
    # color_seq = uname_colors[:tracelen]
    # unametrace = go.Scatter3d(
    #     x=data_dict['players_x'],
    #     y=data_dict['players_y'],
    #     z=data_dict['players_z'],
    #     mode='text',
    #     text=data_dict['usernames'],
    #     textfont=dict(
    #         size=[styles.SCATTERPLOT_TEXT_FONT_SIZE] * tracelen,
    #         color=color_seq[:tracelen],
    #     ),
    # )
    # fig.add_trace(unametrace)
    # fig.update_layout(uniformtext_minsize=styles.SCATTERPLOT_TEXT_FONT_SIZE)

    axlims = data_dict['axis_limits']
    axcolor = {
        'x': styles.SCATTERPLOT_XAXIS_COLOR,
        'y': styles.SCATTERPLOT_YAXIS_COLOR,
        'z': styles.SCATTERPLOT_ZAXIS_COLOR,
    }
    axes = {}
    for coord in ['x', 'y', 'z']:
        min, max = axlims[coord]
        axes[coord] = dict(
            range=(min, max),
            title='',
            zeroline=False,
            showgrid=False,
            showticklabels=False,
            backgroundcolor=axcolor[coord],
        )

    margin = dict(t=0)  # t, b, l, r
    scene = dict(
        xaxis=axes['x'],
        yaxis=axes['y'],
        zaxis=axes['z'],
        aspectmode='cube',
        dragmode='orbit',  # use orbital (not turntable) 3d rotation
        bgcolor=styles.SCATTERPLOT_BG_COLOR,
    )

    fig.update_layout(
        uirevision='constant',  # don't reset axes when updating plot
        showlegend=False,
        scene=scene,
        margin=margin,
    )
    return fig
