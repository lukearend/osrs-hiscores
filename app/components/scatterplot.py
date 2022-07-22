""" Main scatterplot figure. """

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
        style={'height': styles.SCATTERPLOT_HEIGHT}
    )


def hover_template():
    return ("cluster %{customdata[0]}<br>"
            "%{customdata[1]} players<br>"
            "%{customdata[2]:.2f}% unique<br>"
            "median %{customdata[3]}: %{customdata[4]}"
            "<extra></extra>")


def ptsize_fn(x):
    x = np.sqrt(x) * styles.SCATTERPLOT_PTSIZE_CONSTANT
    x = np.minimum(x, styles.SCATTERPLOT_MAX_PTSIZE)
    return x


def cluster_trace(data: Dict[str, Any], ptsize: int) -> go.Scatter3d:
    xyz = np.array(data['cluster_xyz'])
    x = xyz[:, 0]
    y = xyz[:, 1]
    z = xyz[:, 2]

    sizefactor = {
        'small': 1,
        'medium': 2,
        'large': 3
    }[ptsize]
    ptsizes = sizefactor * ptsize_fn(data['cluster_nplayers'])
    ptcolors = np.array(data['cluster_medians'])

    clusterids = np.arange(len(data['cluster_xyz']))
    median_lvls = data['cluster_medians']
    median_lvls = [str(n) if n > 0 else '-' for n in median_lvls]
    hoverdata = list(zip(
        clusterids,
        data['cluster_nplayers'],
        data['cluster_uniqueness'],
        [data['current_skill']] * len(clusterids),
        median_lvls
    ))

    show_inds = data['show_inds']
    return go.Scatter3d(
        x=x[show_inds],
        y=y[show_inds],
        z=z[show_inds],
        mode='markers',
        marker=dict(
            size=ptsizes[show_inds],
            color=ptcolors[show_inds],
            opacity=styles.SCATTERPLOT_PTS_OPACITY,
            colorscale='viridis',
            line=dict(width=0)  # no lines between markers
        ),
        hovertemplate=hover_template(),
        customdata=[d for i, d in enumerate(hoverdata) if i in show_inds]
    )


def halo_traces(data: Dict[str, Any]) -> List[go.Scatter3d]:
    traces = []
    for i, cid in enumerate(data['player_clusterids']):
        nshades = styles.SCATTERPLOT_HALO_NSHADES
        ptsizes = [styles.SCATTERPLOT_HALO_SIZE * i / nshades for i in range(1, nshades + 1)]
        x, y, z = data['cluster_xyz'][cid]

        hovertemplate = "<b>%{customdata[5]}</b><br>" + hover_template()
        median_lvl = data['cluster_medians'][cid]
        hoverdata = [(
            cid,
            data['cluster_nplayers'][cid],
            data['cluster_uniqueness'][cid],
            data['current_skill'],
            '-' if median_lvl == 0 else str(median_lvl),
            data['player_usernames'][i]
        ) for _ in range(nshades)]

        t = go.Scatter3d(
            x=np.full(nshades, x),
            y=np.full(nshades, y),
            z=np.full(nshades, z),
            mode='markers',
            marker=dict(
                size=ptsizes,
                opacity=0.8 * (1 / nshades),
                color='white'
            ),
            hovertemplate=hovertemplate,
            customdata=hoverdata,
            hoverlabel=dict(
                bgcolor=data['player_colors'][i]
            )
        )
        traces.append(t)

    return traces


def annotations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    out_list = []
    for i, uname in enumerate(data['player_usernames']):
        clusterid = data['player_clusterids'][i]
        x, y, z = data['cluster_xyz'][clusterid]
        font = dict(color='white')
        annotation = dict(
            text=uname,
            x=x,
            y=y,
            z=z,
            font=font,
            xanchor='center',
            xshift=0,
            yshift=styles.SCATTERPLOT_HALO_SIZE / 2,
            showarrow=False
        )
        out_list.append(annotation)
    return out_list


@app.callback(
    Output('scatterplot', 'figure'),
    Input('scatterplot-data', 'data'),
    Input('point-size', 'data')
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
        'z': styles.SCATTERPLOT_ZAXIS_COLOR
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
            backgroundcolor=axcolor[coord]
        )

    margin = dict(t=0)  # t, b, l, r
    scene = dict(
        xaxis=axes['x'],
        yaxis=axes['y'],
        zaxis=axes['z'],
        aspectmode='cube',
        dragmode='orbit',  # use orbital (not turntable) 3d rotation
        bgcolor=styles.SCATTERPLOT_BG_COLOR,
        annotations=player_unames
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
        margin=margin
    )
    return fig
