""" Code for Plotly figures. """

from typing import Tuple, Dict, List

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from numpy.typing import NDArray
from pandas import DataFrame

from src.app.helpers import load_skill_icon


def get_scatterplot(df: DataFrame,
                    colorbar_label: str,
                    colorbar_ticks: List[int],
                    axis_limits: Dict[str, NDArray],
                    size_factor: int,
                    player_crosshairs: Tuple = None,
                    clicked_crosshairs: Tuple = None) -> go.Figure:

    cmin = colorbar_ticks[0]
    cmax = colorbar_ticks[-1]

    # go.Scatter3d would be preferred but it doesn't allow
    # color and hover data formatting using a dataframe.
    fig = px.scatter_3d(
        df,
        x='x',
        y='y',
        z='z',
        color='level',
        range_color=(cmin, cmax),
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
                line_color='blue',
                line_width=3 * size_factor,
                showlegend=False,
                hoverinfo='none',
                hovertemplate=None
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
                line_width=3 * size_factor,
                showlegend=False,
                hoverinfo='none',
                hovertemplate=None
            )
        )

    fig.update_layout(
        uirevision='constant',  # don't reset axes after updating plot
        scene=dict(
            aspectmode='cube',
            xaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[xmin, xmax],
                backgroundcolor='#222222'
            ),
            yaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[ymin, ymax],
                backgroundcolor='#242424'
            ),
            zaxis=dict(
                title='', showticklabels=False, showgrid=False,
                zeroline=False, range=[zmin, zmax],
                backgroundcolor='#202020'
            )
        ),
        coloraxis_colorbar=dict(
            title=dict(
                text=colorbar_label,
                side='right'
            ),
            tickvals=colorbar_ticks,
            tickfont={'family': "rs-regular"},
            xanchor='right',
            len=0.9
        )
    )

    fig.update_layout(scene_dragmode='orbit')  # use orbital rotation by default

    return fig


def get_empty_boxplot(split: str, split_skills: List[str]) -> go.Figure:

    nskills = len(split_skills)
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
        layout_margin=dict(b=20, l=2, r=0, t=0),  # left margin adds space for y tick numbers
        layout_xaxis_tickvals=[],                 # bottom margin adds space for x tick icons
        layout_xaxis_range=np.array([0, nskills]) - 0.5,
        layout_yaxis_range=[1, 106],
        layout_yaxis_tickvals=[1, 20, 40, 60, 80, 99],
        layout_yaxis_tickfont={'family': "rs-regular"},
        layout_xaxis_fixedrange=True,
        layout_yaxis_fixedrange=True
    )

    for i, skill in enumerate(split_skills):
        fig.add_layout_image(dict(
            source=load_skill_icon(skill),
            xref="x",          # x has units of x-coordinate on figure
            yref="paper",      # y has units fraction of figure size
            xanchor="center",
            yanchor="top",
            x=i,
            y=-0.01,
            sizex=1,
            sizey=0.1,         # limits how large icons grow when displaying split 'cb'
            layer="above"
        ))

    return fig
