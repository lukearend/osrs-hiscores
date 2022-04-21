import os
from typing import Tuple, Dict

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from PIL import Image
from numpy.typing import NDArray
from pandas import DataFrame

from app import load_boxplot_tick_labels, assets_dir, load_boxplot_x_offsets


def get_scatterplot(df: DataFrame,
                    colorbar_label: str,
                    colorbar_limits: Tuple[int],
                    axis_limits: Dict[str, NDArray],
                    size_factor: int,
                    player_crosshairs: Tuple = None,
                    clicked_crosshairs: Tuple = None) -> go.Figure:

    # While go.Scatter3d (from graph objects module) would be preferred,
    # it doesn't allow color and hover data formatting using a dataframe.
    fig = px.scatter_3d(
        df,
        x='x',
        y='y',
        z='z',
        color='level',
        range_color=colorbar_limits,
        hover_name=[f"Cluster {i}" for i in df['id']],
        custom_data=['id', 'size', 'uniqueness']
    )

    hover_box = '<br>'.join([
        '<b>Cluster %{customdata[0]}</b>',
        '%{customdata[1]} players',
        '%{customdata[2]:.2f}% unique'
    ])
    fig.update_traces(hovertemplate=hover_box)

    point_sizes = size_factor * np.sqrt(np.minimum(15000, df['size'])) * 0.15
    fig.update_traces(
        marker=dict(
            size=point_sizes,
            line=dict(width=0),
            opacity=0.5
        )
    )

    xmin, xmax = axis_limits['x']
    ymin, ymax = axis_limits['y']
    zmin, zmax = axis_limits['z']

    if player_crosshairs is not None:
        x, y, z = player_crosshairs
        fig.add_trace(
            go.Scatter3d(
                x=[xmin, xmax, None, x, x, None, x, x],
                y=[y, y, None, ymin, ymax, None, y, y],
                z=[z, z, None, z, z, None, zmin, zmax],
                mode='lines',
                line_color='white',
                line_width=3,
                showlegend=False,
                hoverinfo='skip'
            )
        )

    if clicked_crosshairs is not None:
        x, y, z = clicked_crosshairs
        fig.add_trace(
            go.Scatter3d(
                x=[xmin, xmax, None, x, x, None, x, x],
                y=[y, y, None, ymin, ymax, None, y, y],
                z=[z, z, None, z, z, None, zmin, zmax],
                mode='lines',
                line_color='red',
                line_width=3,
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
                backgroundcolor='rgb(230, 230, 230)'
            ),
            yaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[ymin, ymax],
                backgroundcolor='rgb(220, 220, 220)'
            ),
            zaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[zmin, zmax],
                backgroundcolor='rgb(200, 200, 200)'
            )
        ),
        coloraxis_colorbar=dict(
            title=dict(
                text=colorbar_label,
                side='right'
            ),
            xanchor='right'
        )
    )

    return fig


def get_empty_boxplot(split: str) -> go.Figure:

    tick_labels = load_boxplot_tick_labels(split)
    nskills = len(tick_labels)

    nans = np.full(nskills, np.nan)
    fig = go.Figure(
        data=[
            go.Box(
                lowerfence=nans,
                q1=nans,
                median=nans,
                q3=nans,
                upperfence=nans
            )
        ],
        layout_uirevision='constant',
        layout_margin=dict(b=0, l=0, r=0, t=0),
        layout_xaxis_tickvals=[],
        layout_xaxis_range=np.array([0, nskills]) - 0.5,
        layout_yaxis_range=[-15, 100],
        layout_yaxis_tickvals=[1, 20, 40, 60, 80, 99],
    )

    icon_x_offset = load_boxplot_x_offsets(split)
    for i, skill in enumerate(tick_labels):
        icon_path = os.path.join(assets_dir(), "icons", f"{skill}_icon.png")
        icon = Image.open(icon_path)
        fig.add_layout_image(dict(
            source=icon,
            xref="x",
            yref="y",
            x=i - icon_x_offset,
            y=-2,
            sizex=1,
            sizey=12,
            sizing="contain",
            layer="above"
        ))

    return fig
