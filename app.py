#!/usr/bin/env python3

""" Visualize 3d-embedded cluster data with a Dash application. """

import pickle

from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import mydcc
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


print('loading data...')
print(30 * '\n')

with open('data/processed/dimreduced.pkl', 'rb') as f:
    xyz = pickle.load(f)
with open('data/processed/centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)
with open('data/processed/clusters.pkl', 'rb') as f:
    clusters = pickle.load(f)
# with open('data/processed/players.pkl', 'rb') as f:
#     players = pickle.load(f)
with open('reference/skills.csv', 'r') as f:
    skills = f.read().strip().split('\n')


# Convert input data into dataframes for plotting.
data = {}
for split, xyz_data in xyz.items():
    num_clusters = len(xyz_data)
    cluster_sizes = clusters[split]['cluster_sizes']

    if split == 'all':
        split_skills = skills
    elif split == 'cb':
        split_skills = skills[:8]
    elif split == 'noncb':
        split_skills = [skills[0]] + skills[8:]

    percentile_data = np.zeros((num_clusters, 3 * len(split_skills)), dtype='int')
    percentile_columns = []
    for i, percentile in enumerate((5, 50, 95)):
        for j, skill in enumerate(split_skills):
            col_i = i * len(split_skills) + j
            percentile_data[:, col_i] = np.floor(centroids[split][percentile][:, j])
            percentile_columns.append("{}_{}".format(skill, percentile))

    cluster_sizes = np.expand_dims(cluster_sizes, axis=1)
    data_array = np.concatenate([xyz_data, cluster_sizes, percentile_data], axis=1)
    columns = ['x', 'y', 'z', 'size'] + percentile_columns

    df = pd.DataFrame(data_array,
                      columns=columns,
                      index=np.arange(1, num_clusters + 1))
    data[split] = df


# Define main scatterplot figure.
def get_scatterplot(split, skill):
    fig = px.scatter_3d(data[split], x='x', y='y', z='z',
                        color="{}_50".format(skill),
                        hover_data={'x': False, 'y': False, 'z': False,
                                    'cluster': data[split].index, 'size': True,
                                    '{}_95'.format(skill): True,
                                    '{}_50'.format(skill): True,
                                    '{}_5'.format(skill): True})

    fig.update_layout(
        margin=dict(b=0, l=0, r=0, t=0),
        scene=dict(
            aspectmode='cube',
            xaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False,
                       backgroundcolor='rgb(230, 230, 230)'),
            yaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False,
                       backgroundcolor='rgb(240, 240, 240)'),
            zaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False,
                       backgroundcolor='rgb(200, 200, 200)')
        )
    )

    # Point size is proportional to cluster size.
    fig.update_traces(
        marker=dict(
            size=3 * np.log(clusters[split]['cluster_sizes']),
            line=dict(width=0),
            opacity=0.5
        )
    )

    return fig


# Run Dash app displaying graphics.
app = Dash(__name__)
app.layout = dbc.Container([

    # Intro matters.
    dbc.Row(dbc.Col(html.H1(children=html.Strong('OSRS player clusters')))),

    dbc.Row(dbc.Col(html.Div(children='''
        Each point represents a cluster of OSRS players with similar combat
        stats. The closer two clusters are, the more similar the accounts are
        in each of those two clusters. Some clusters contain only a single
        (highly) unique player; others comprise thousands or tens of thousands
        of similar accounts. The size of each point corresponds to the number
        of players in that cluster. The clusters are color-coded by total
        level; axes have no meaningful units.
    '''))),

    # Split selector.
    dbc.Row(dbc.Col(
        dcc.Dropdown(
            id='split-dropdown',
            options=[
                {'label': 'All skills','value': 'all'},
                {'label': 'Combat skills','value': 'cb'},
                {'label': 'Non-combat skills','value': 'noncb'},
            ],
            value='all')
    )),

    # Skill selector.
    dbc.Row(dbc.Col(
        dcc.Dropdown(
            id='skill-dropdown',
            options=[
                {'label': skillname[0].upper() + skillname[1:].replace('_', ' '),
                 'value': skillname} for skillname in skills
            ],
            value='total')
    )),

    # Username input.
    dbc.Row([
        dbc.Col(dcc.Input(id='username-input', type='text', placeholder='input username')),
        dbc.Col(html.Div(id='selected-user'))
    ]),

    # Scatterplot.
    dbc.Row(dbc.Col(
        dcc.Graph(id='scatter-plot',
                  figure=get_scatterplot('all', 'total'),
                  style={'height': '90vh'},
                  clear_on_unhover=True),
    )),
    dcc.Tooltip(id='tooltip'),
    dbc.Row(dbc.Col(html.Div(id='dummy-content'))),
    # mydcc.Change_trace_mapbox(id='change-trace', aim='scatter-plot')
])


# Grey out skills in dropdown depending on current split.
@app.callback(
    Output('skill-dropdown', 'options'),
    Output('skill-dropdown', 'value'),
    Input('split-dropdown', 'value')
)
def select_split(split):
    disabled = {
        'all': [],
        'cb': skills[8:],
        'noncb': skills[1:8]
    }[split]

    options = []
    for skill in skills:
        options.append({
            'label': skill[0].upper() + skill[1:].replace('_', ' '),
            'value': skill,
            'disabled': True if skill in disabled else False
        })

    return options, 'total'


# Print out cluster info for selected player.
@app.callback(
    Output('selected-user', 'children'),
    [Input('username-input', 'value'), Input('split-dropdown', 'value')],
)
def select_player(username, split):
    if username:
        key = username.lower()
        try:
            # cluster_id = players[split][key]['cluster_id']
            # name = players[split][key]['name']
            return "no players loaded"
        except KeyError:
            return "no player '{}' in dataset".format(value)
        return "'{}' cluster ID: {}".format(name, cluster_id)

    return ''


# Highlight currently hovered point.
@app.callback(
    Output('scatter-plot', 'figure'),
    Input('scatter-plot', 'hoverData'),
    State('scatter-plot', 'figure'),
)
def select_point(hoverData, fig):
    if hoverData:
        print(hoverData['points'][0]['pointNumber'])

    return fig


# @app.callback(
#     Output('dummy-content', 'children'),
#     Input('scatter-plot', 'hoverData'),
# )
# def print_stats(hoverData):
#     if hoverData is None:
#         return no_update

#     cluster_id = hoverData['points'][0]['pointNumber']

#     median = np.floor(centroids[SPLIT][50][cluster_id]).astype('int')
#     upper = np.floor(centroids[SPLIT][95][cluster_id]).astype('int')
#     lower = np.floor(centroids[SPLIT][5][cluster_id]).astype('int')

#     header = "cluster {}: {} players".format(
#         cluster_id, clusters[SPLIT]['cluster_sizes'][cluster_id])

#     # Clear previous.
#     print('\033[28A')
#     print(30 * (30 * ' ' + '\n'))

#     print(header)
#     print('-' * len(header))
#     for skill, med, low, up in zip(skills, median, lower, upper):
#         lvl_text = str(med).ljust(2) + " ({}-{})".format(low, up)
#         print(skill.ljust(12), lvl_text)
#     print()

#     return no_update


if __name__ == '__main__':
    app.run_server(debug=True)
