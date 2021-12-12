import numpy as np

import plotly.express as px
import plotly.graph_objects as go

from app import skill_pretty


def get_scatterplot(split_data, skill, level_range, highlight_cluster=None):

    if skill == 'total':
        color_range = [500, 2277]
    else:
        color_range = [1, 99]

    # When level selector is used, we display only those clusters whose
    # interquartile range in the chosen skill overlaps the selected range.

    skill_i = split_data['skills'].index(skill)
    show_inds = np.where(np.logical_and(
        split_data['cluster_stats'][:, skill_i, 3] >= level_range[0],   # 75th percentile
        split_data['cluster_stats'][:, skill_i, 1] <= level_range[1],   # 25th percentile
    ))[0]
    clusters_xyz = split_data['xyz'][show_inds]

    # We use a px.scatter_3d instead of a go.Scatter3d because it
    # is much easier for color and hover data formatting.

    fig = px.scatter_3d(
        x=clusters_xyz[:, 0],
        y=clusters_xyz[:, 1],
        z=clusters_xyz[:, 2],
        color=split_data['cluster_stats'][:, skill_i, 2],               # 50th percentile (median)
        range_color=color_range,
        hover_data={
            'cluster': np.arange(1, len(clusters_xyz) + 1), 'size': split_data['cluster_sizes']
        }
    )

    sizes = split_data['cluster_sizes'][show_inds]
    fig.update_traces(
        marker=dict(
            size=3 * np.log(sizes + 1),
            line=dict(width=0),
            opacity=0.5
        )
    )

    if highlight_cluster is not None:
        x = clusters_xyz[highlight_cluster, 0]
        y = clusters_xyz[highlight_cluster, 1]
        z = clusters_xyz[highlight_cluster, 2]
        fig.add_trace(
            go.Scatter3d(
                x=[xmin, xmax, None, x, x, None, x, x],
                y=[y, y, None, ymin, ymax, None, y, y],
                z=[z, z, None, z, z, None, zmin, zmax],
                mode='lines',
                line_color='white',
                line_width=2,
                showlegend=False,
                name='crosshairs'
            )
        )

    fig.update_traces(hoverinfo='none', hovertemplate=None)

    xmin, xmax = split_data['axis_limits']['x']
    ymin, ymax = split_data['axis_limits']['y']
    zmin, zmax = split_data['axis_limits']['z']

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
                text=skill_pretty(skill).replace(' ', '\n'),
                side='right'
            ),
            xanchor='right'
        )
    )

    return fig


def get_boxplot(percentile_data):
    fig = go.Figure()

    # Don't show total level.
    percentile_data = percentile_data[1:]

    mins = percentile_data[:, 0]
    maxes = percentile_data[:, 4]
    median = percentile_data[:, 2]
    q1 = percentile_data[:, 1]
    q3 = percentile_data[:, 3]
    iqr = q3 - q1

    lowerfence = q1 - 1.5 * iqr
    upperfence = q3 + 1.5 * iqr

    fig = go.Figure(
        data=[
            go.Box(
                lowerfence=np.maximum(mins, lowerfence),
                q1=q1,
                median=median,
                q3=q3,
                upperfence=np.minimum(maxes, upperfence)
            )
        ]
    )

    return fig
