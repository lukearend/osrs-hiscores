import numpy as np
import pandas
import pandas as pd

import plotly.express as px
import plotly.graph_objects as go

from app import skill_pretty


def get_scatterplot(split_data, skill, level_range, point_size,
                    n_neighbors, min_dist, highlight_cluster=None):

    if skill == 'total':
        color_range = [500, 2277]
    else:
        color_range = [1, 99]

    # When level selector is used, we display only those clusters whose
    # interquartile range in the chosen skill overlaps the selected range.

    skill_i = split_data['skills'].index(skill)
    show_inds = np.where(np.logical_and(
        split_data['cluster_quartiles'][:, 3, skill_i] >= level_range[0],   # 75th percentile
        split_data['cluster_quartiles'][:, 1, skill_i] <= level_range[1],   # 25th percentile
    ))[0]

    xyz_df = pd.DataFrame(split_data['xyz'][n_neighbors][min_dist][show_inds], columns=['x', 'y', 'z'])
    info_df = pd.DataFrame({
        'cluster_id': show_inds + 1,
        'num_players': split_data['cluster_sizes'][show_inds],
        'uniqueness': 100 * split_data['cluster_uniqueness'][show_inds],
        'median': split_data['cluster_quartiles'][:, 2, skill_i][show_inds],
        'min': split_data['cluster_quartiles'][:, 0, skill_i][show_inds],
        'max': split_data['cluster_quartiles'][:, 4, skill_i][show_inds],
        'q1': split_data['cluster_quartiles'][:, 1, skill_i][show_inds],
        'q3': split_data['cluster_quartiles'][:, 3, skill_i][show_inds],
    })
    df = pd.concat([xyz_df, info_df], axis=1)

    # We use a px.scatter_3d instead of a go.Scatter3d because it
    # is much easier for color and hover data formatting.

    fig = px.scatter_3d(
        df,
        x='x',
        y='y',
        z='z',
        color='median',
        range_color=color_range,
        hover_name=[f'Cluster {i}' for i in df['cluster_id']],
        custom_data=['cluster_id', 'num_players', 'uniqueness', 'min', 'q1', 'median', 'q3', 'max']
    )

    hover_box = '<br>'.join([
        '<b>Cluster %{customdata[0]}</b>',
        '%{customdata[1]} players',
        '%{customdata[2]:.2f}% unique',
        f'{skill_pretty(skill)} quantiles:',
        '[%{customdata[3]:d}, %{customdata[4]:d}, %{customdata[5]:d}, %{customdata[6]:d}, %{customdata[7]:d}]'
    ])
    fig.update_traces(hovertemplate=hover_box)

    size_factor = {
        'small': 1,
        'medium': 2,
        'large': 3
    }[point_size]

    sizes = split_data['cluster_sizes'][show_inds]
    fig.update_traces(
        marker=dict(
            size=size_factor * np.log(sizes + 1),
            line=dict(width=0),
            opacity=0.5
        )
    )

    xmin, xmax = split_data['axis_limits'][n_neighbors][min_dist]['x']
    ymin, ymax = split_data['axis_limits'][n_neighbors][min_dist]['y']
    zmin, zmax = split_data['axis_limits'][n_neighbors][min_dist]['z']

    if highlight_cluster is not None:
        x, y, z = split_data['xyz'][n_neighbors][min_dist][highlight_cluster - 1]
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

    percentile_data = percentile_data[:, 1:]    # Drop total level.
    mins, q1, median, q3, maxes = percentile_data

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
        ],
        layout=dict(margin=dict(l=0, r=0, t=0, b=0))
    )

    return fig
