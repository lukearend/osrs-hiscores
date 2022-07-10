from typing import Dict, Any, List

import dash_core_components as dcc
import numpy as np
from plotly import graph_objects as go
from dash import Output, Input, no_update

from app import app, styles


def scatterplot():
    return dcc.Graph(
        id='scatterplot',
        className='scatterplot-graph',
        clear_on_unhover=True,
        style={
            'height': styles.SCATTERPLOT_HEIGHT,
        }
    )


def hover_template():
    return ("cluster %{customdata[0]}<br>"
            "%{customdata[1]} players<br>"
            "%{customdata[2]:.2f}% unique"
            "<extra></extra>")


def halo_hover_template():
    return "%{customdata[3]}<br>" + hover_template()


def hover_data(ids, nplayers, uniqueness):
    return list(zip(ids, nplayers, uniqueness))


def halo_hover_data(ids, nplayers, uniqueness, usernames):
    return list(zip(ids, nplayers, uniqueness, usernames))


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

    clusterids = np.arange(len(data['cluster_xyz']))
    hoverdata = hover_data(
        ids=clusterids,
        nplayers=data['cluster_nplayers'],
        uniqueness=data['cluster_uniqueness']
    )

    x, y, z = zip(*data['cluster_xyz'])
    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=ptsizes,
            color=data['cluster_medians'],
            opacity=styles.SCATTERPLOT_PTS_OPACITY,
            line=dict(width=0),  # hide lines bounding the marker points
            colorscale='viridis',
        ),
        hovertemplate=hover_template(),
        customdata=hoverdata,
    )


def halo_traces(data: Dict[str, Any]) -> List[go.Scatter3d]:
    player_clusterids = data['player_clusterids']
    nshades = styles.SCATTERPLOT_HALO_NSHADES

    hovertemplate = halo_hover_template()
    hoverdata = halo_hover_data(
        ids=player_clusterids,
        nplayers=[data['cluster_nplayers'][i] for i in player_clusterids],
        uniqueness=[data['cluster_uniqueness'][i] for i in player_clusterids],
        usernames=data['player_usernames']
    )

    traces = []
    for i in range(nshades):
        x, y, z = zip(*[data['cluster_xyz'][i] for i in player_clusterids])
        ptsize = (nshades - i) / nshades * styles.SCATTERPLOT_HALO_SIZE
        t = go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode='markers',
            marker=dict(
                size=ptsize,
                opacity=1 / nshades,
                color=data['player_colors'],
            ),
            hovertemplate=hovertemplate,
            customdata=hoverdata,
        )
        traces.append(t)

    return traces


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

    if data['player_usernames']:
        for t in halo_traces(data):
            fig.add_trace(t)

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
