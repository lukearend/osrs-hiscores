import numpy as np

import plotly.express as px
import plotly.graph_objects as go


def get_scatterplot(appdata, skill, level_range, highlight_cluster=None):

    if skill == 'total':
        color_range = [500, 2277]
    else:
        color_range = [1, 99]

    # When level selector is used, we display only those clusters whose
    # interquartile range in the chosen skill overlaps the selected range.
    inds = np.where(np.logical_and(
        appdata['percentiles']['{}_75'.format(skill)] >= level_range[0],
        appdata['percentiles']['{}_25'.format(skill)] <= level_range[1],
    ))[0]
    plot_data = appdata['xyz'].iloc[inds]

    xmin, xmax = appdata['axis_limits']['x']
    ymin, ymax = appdata['axis_limits']['y']
    zmin, zmax = appdata['axis_limits']['z']

    # We use a px.scatter_3d instead of a go.Scatter3d because the former
    # is better for color and hover data formatting.
    fig = px.scatter_3d(
        plot_data,
        x='x', y='y', z='z',
        color='{}_50'.format(skill),
        range_color=color_range,
        hover_data={
            'x': False, 'y': False, 'z': False,
            'cluster': plot_data.index + 1, 'size': True,
            '{}_95'.format(skill): True,
            '{}_50'.format(skill): True,
            '{}_5'.format(skill): True
        }
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

    sizes = appdata['cluster_sizes'][inds]
    fig.update_traces(
        marker=dict(
            size=3 * np.log(sizes + 1),
            line=dict(width=0),
            opacity=0.5
        )
    )

    if highlight_cluster is not None:
        x = appdata['xyz']['x'][highlight_cluster]
        y = appdata['xyz']['y'][highlight_cluster]
        z = appdata['xyz']['z'][highlight_cluster]
        fig.add_trace(
            go.Scatter3d(
                x=[xmin, xmax, None, x, x, None, x, x],
                y=[y, y, None, ymin, ymax, None, y, y],
                z=[z, z, None, z, z, None, zmin, zmax],
                mode='lines',
                line_color='white',
                line_width=2,
                name='crosshairs'
            )
        )

    fig.update_traces(hoverinfo='none', hovertemplate=None)
    fig.update_traces(showlegend=False, selector=dict(name='crosshairs'))

    return fig


def get_boxplot(percentiles, cluster_id):
    return None
