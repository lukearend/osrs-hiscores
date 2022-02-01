import json
import pathlib

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from PIL import Image


def get_scatterplot(df, colorlims, colorlabel, pointsize, axlims, crosshairs=None):
    # px.scatter_3d works better than go.Scatter3d
    # for color and hover data formatting.
    # todo: with new refactoring, can I use a go.Scatter3d graph object here instead?
    fig = px.scatter_3d(
        df,
        x='x',
        y='y',
        z='z',
        color='level',
        range_color=colorlims,
        hover_name=[f"Cluster {i}" for i in df['id']],
        custom_data=['id', 'size', 'uniqueness']
    )

    hover_box = '<br>'.join([
        '<b>Cluster %{customdata[0]}</b>',
        '%{customdata[1]} players',
        '%{customdata[2]:.2f}% unique'
    ])
    fig.update_traces(hovertemplate=hover_box)

    point_sizes = pointsize * np.log(df['size'] + 1)
    fig.update_traces(
        marker=dict(
            size=point_sizes,
            line=dict(width=0),
            opacity=0.5
        )
    )

    xmin, xmax = axlims['x']
    ymin, ymax = axlims['y']
    zmin, zmax = axlims['z']

    if crosshairs is not None:
        x, y, z = crosshairs
        fig.add_trace(
            go.Scatter3d(
                x=[xmin, xmax, None, x, x, None, x, x],
                y=[y, y, None, ymin, ymax, None, y, y],
                z=[z, z, None, z, z, None, zmin, zmax],
                mode='lines',
                line_color='white',
                line_width=2,
                showlegend=False,
                hoverinfo='skip'
            )
        )

    fig.update_layout(
        uirevision='constant',
        margin=dict(b=0, l=0, r=0, t=0),
        scene=dict(
            aspectmode='cube',
            xaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[xmin, xmax],
                backgroundcolor='rgb(230, 230, 230)'),
            yaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[ymin, ymax],
                backgroundcolor='rgb(220, 220, 220)'),
            zaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[zmin, zmax],
                backgroundcolor='rgb(200, 200, 200)')
        ),
        coloraxis_colorbar=dict(
            title=dict(
                text=colorlabel,
                side='right'
            ),
            xanchor='right'
        )
    )

    return fig


def get_boxplot(split, data=None):
    layout_file = pathlib.Path(__name__).resolve().parent / 'assets' / 'boxplot_ticks.json'
    with open(layout_file, 'r') as f:
        tick_labels = json.load(f)[split]

    if data is None:
        nans = {
            'all': 23 * [np.nan],
            'cb': np.full(7, np.nan),
            'noncb': np.full(16, np.nan)
        }[split]
        data = {q: nans for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']}

    fig = go.Figure(
        data=[
            go.Box(
                lowerfence=data['lowerfence'],
                q1=data['q1'],
                median=data['median'],
                q3=data['q3'],
                upperfence=data['upperfence']
            )
        ],
        layout_uirevision='constant',
        layout_margin=dict(b=0, l=0, r=0, t=0),
        layout_xaxis_tickvals=[],
        layout_yaxis_range=[-15, 100],
        layout_yaxis_tickvals=[1, 20, 40, 60, 80, 99],
    )

    icon_offset_x = {'all': 0.43, 'cb': 0.13, 'noncb': 0.30}[split]
    for i, skill in enumerate(tick_labels):
        icon = Image.open(f"/Users/lukearend/projects/osrs-hiscores/app/assets/icons/{skill}_icon.png")
        fig.add_layout_image(
            dict(
                source=icon,
                xref="x",
                yref="y",
                x=i - icon_offset_x,
                y=-2,
                sizex=1,
                sizey=12,
                sizing="contain",
                layer="above")
        )
    return fig
