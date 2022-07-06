from typing import Dict, Any, List

import dash_core_components as dcc
import numpy as np
from plotly import graph_objects as go
from dash import Output, Input, no_update

from app import app, styles


def scatterplot():
    return dcc.Graph(
        id='scatterplot',
        figure={},
        className='scatterplot-graph',
        style={
            'height': styles.SCATTERPLOT_HEIGHT,
        }
    )


def ptsize_fn(x):
    x = np.sqrt(x) * styles.SCATTERPLOT_PTSIZE_CONSTANT
    x = np.maximum(x, styles.SCATTERPLOT_MAX_PTSIZE)
    return x


def cluster_trace(data: Dict[str, Any], ptsize: int) -> go.Scatter3d:
    sizefactor = {
        'small': 1,
        'medium': 2,
        'large': 3,
    }[ptsize]
    ptsizes = sizefactor * ptsize_fn(data['cluster_nplayers'])

    x, y, z = zip(*data['cluster_xyz'])
    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=ptsizes,
            color=data['cluster_total_lvl'],
            opacity=styles.SCATTERPLOT_PTS_OPACITY,
            line=dict(width=0),  # hide lines bounding the marker points
        ),
    )


def halo_trace(data: Dict[str, Any]) -> List[go.Scatter3d]:
    if not data['player_usernames']:
        return go.Scatter3d()

    nshades = styles.SCATTERPLOT_HALO_NSHADES
    trace_xyz = []
    trace_ptsize = []
    trace_ptcolor = []
    for player_i, clusterid in enumerate(data['player_clusterids']):
        x, y, z = data['cluster_xyz'][clusterid]
        color = data['player_colors'][player_i]
        for i in range(nshades):
            ptsize = (i + 1) / nshades * styles.SCATTERPLOT_HALO_SIZE
            trace_xyz.append((x, y, z))
            trace_ptsize.append(ptsize)
            trace_ptcolor.append(color)

    x, y, z = zip(*trace_xyz)
    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=trace_ptsize,
            color=trace_ptcolor,
            opacity=1 / nshades,
        ),
    )


def annotations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out_list = []
    for i, uname in enumerate(data['player_usernames']):
        clusterid = data['player_clusterids'][i]
        x, y, z = data['cluster_xyz'][clusterid]
        font = dict(
            color='white',
        )
        annotation = dict(
            text=uname,
            x=x,
            y=y,
            z=z,
            font=font,
            xanchor='center',
            xshift=0,
            yshift=styles.SCATTERPLOT_HALO_SIZE / 2,
            showarrow=False,
        )
        out_list.append(annotation)
    return out_list


@app.callback(
    Output('scatterplot', 'figure'),
    Input('scatterplot-data', 'data'),
    Input('point-size', 'data'),
)
def redraw_scatterplot(data: Dict[str, Any], ptsize: int) -> go.Figure:
    if not data:
        return no_update

    main_trace = cluster_trace(data, ptsize)
    player_halos = halo_trace(data)
    player_unames = annotations(data)

    axlims = data['axis_limits']
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
        annotations=player_unames,
    )

    fig = go.Figure()
    fig.add_trace(main_trace)
    fig.add_trace(player_halos)
    fig.update_layout(
        uirevision='constant',  # don't reset axes when updating plot
        showlegend=False,
        scene=scene,
        margin=margin,
    )
    return fig


# todo: use this with range slider
# @app.callback(
#     Output('scatterplot', 'extendData'),
#     Input('
#     State('scatterplot-data', 'data'),
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
