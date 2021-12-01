#!/usr/bin/env python3

""" Visualize 3d-embedded cluster data with a Dash application. """

import pickle

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.express as px
import pandas as pd
from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


db = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5)['osrs-hiscores']
players = db['players']
try:
    db.command('ping')
except ServerSelectionTimeoutError:
    raise ValueError("could not connect to mongodb")

print('connected to mongo')
print('loading data...')

with open('data/processed/dimreduced.pkl', 'rb') as f:
    xyz = pickle.load(f)
with open('data/processed/centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)
with open('data/processed/clusters.pkl', 'rb') as f:
    clusters = pickle.load(f)
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
def get_scatterplot(split, skill, level_range):

    if skill == 'total':
        color_range = [500, 2277]
    else:
        color_range = [1, 99]

    inds = np.where(np.logical_and(
        data[split]['{}_95'.format(skill)] >= level_range[0],
        data[split]['{}_5'.format(skill)] <= level_range[1],
    ))[0]
    plot_data = data[split].iloc[inds]

    fig = px.scatter_3d(plot_data, x='x', y='y', z='z',
                        color='{}_50'.format(skill),
                        range_color=color_range,
                        hover_data={'x': False, 'y': False, 'z': False,
                                    'cluster': plot_data.index, 'size': True,
                                    '{}_95'.format(skill): True,
                                    '{}_50'.format(skill): True,
                                    '{}_5'.format(skill): True})

    fig.update_traces(hoverinfo='none', hovertemplate=None)

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
        ),
        coloraxis_colorbar=dict(title=skill_pretty(skill))
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


def skill_pretty(skill):
    return skill[0].upper() + skill[1:].replace('_', ' ') + ' level'

def get_level_marks(skill):
    if skill == 'total':
        return {i: str(i) for i in [1, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2277]}
    else:
        return {i: str(i) for i in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]}


# Run Dash app displaying graphics.
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([

    dbc.Row(
        dbc.Col([
            html.Br(),
            html.H1(children=html.Strong('OSRS player clusters')),
            html.Div(children='''
                Each point represents a cluster of OSRS players with similar combat
                stats. The closer two clusters are, the more similar the accounts are
                in each of those two clusters. Some clusters contain only a single
                (highly) unique player; others comprise thousands or tens of thousands
                of similar accounts. The size of each point corresponds to the number
                of players in that cluster. Axes have no meaningful interpretation.
            '''),
            html.Br(),
        ])
    ),

    dbc.Row([
        dbc.Col(html.Div(children="Cluster players by:"), width=2),
        dbc.Col(dcc.Dropdown(
            id='split-dropdown',
            options=[
                {'label': 'All skills','value': 'all'},
                {'label': 'Combat skills','value': 'cb'},
                {'label': 'Non-combat skills','value': 'noncb'},
            ],
            value='all' 
        ), width=4),
        dbc.Col(html.Div(children="Color clusters by:"), width=2),
        dbc.Col(dcc.Dropdown(
            id='skill-dropdown',
            options=[
                {'label': skill_pretty(skill),
                 'value': skill} for skill in skills
            ],
            value='total'
        ), width=4)
    ], align='center', style={'padding-bottom': '1vh'}),

    dbc.Row([
        dbc.Col(html.Div(children="Show levels:"), width='auto'),
        dbc.Col(dcc.RangeSlider(
            id='level-selector',
            min=1,
            max=2277,
            step=1,
            value=[1, 2277],
            marks=get_level_marks('total')
        ))
    ], align='center', style={'padding-bottom': '1vh'}),

    dbc.Row([
        dbc.Col(html.Div(children="Lookup player:"), width='auto'),
        dbc.Col(dcc.Input(id='username-input', type='text', placeholder="e.g. 'snakeylime'"), width='auto'),
        dbc.Col(html.Div(id='selected-user'), width='auto'),
    ], align='center', style={'padding-bottom': '1vh'}),

    dbc.Row(
        dbc.Col([
            dcc.Graph(id='scatter-plot',
                      figure=get_scatterplot('all', 'total', [1, 2277]),
                      style={'height': '80vh'},
                      clear_on_unhover=True),
            html.Br()
        ])
    ),
    dcc.Tooltip(id='tooltip')
])


# Callbacks for dynamic updating of Dash app.
@app.callback(
    Output('scatter-plot', 'figure'),
    Input('split-dropdown', 'value'),
    Input('skill-dropdown', 'value'),
    Input('level-selector', 'value')
)
def redraw_figure(split, skill, level_range):
    min_level, max_level = level_range
    return get_scatterplot(split, skill, level_range)


@app.callback(
    Output('skill-dropdown', 'options'),
    Output('skill-dropdown', 'value'),
    Input('split-dropdown', 'value'),
    State('skill-dropdown', 'value')
)
def choose_split(split, current_skill):
    if split:
        disabled = {
            'all': [],
            'cb': skills[8:],
            'noncb': skills[1:8]
        }[split]

        options = []
        for skill in skills:
            options.append({
                'label': skill_pretty(skill),
                'value': skill,
                'disabled': True if skill in disabled else False
            })

        if current_skill in disabled:
            new_skill = 'total'
        else:
            new_skill = current_skill

        return options, new_skill

    raise PreventUpdate


@app.callback(
    Output('level-selector', 'min'),
    Output('level-selector', 'max'),
    Output('level-selector', 'value'),
    Output('level-selector', 'marks'),
    Input('skill-dropdown', 'value'),
    State('level-selector', 'value')
)
def choose_skill(new_skill, current_range):
    if new_skill:
        if current_range == [1, 2277] and new_skill != 'total':
            new_range = [1, 99]
        elif new_skill == 'total':
            new_range = [1, 2277]
        else:
            new_range = current_range

        marks = get_level_marks(new_skill)

        if new_skill == 'total':
            return 1, 2277, new_range, marks
        return 1, 99, new_range, marks

    raise PreventUpdate


@app.callback(
    Output('selected-user', 'children'),
    Input('username-input', 'value'),
    Input('split-dropdown', 'value')
)
def lookup_player(username, split):
    if username:
        player = players.find_one({'_id': username.lower()})
        if player:
            username = player['username']
            cluster_id = player['cluster_id'][split]
            uniqueness = clusters[split]['percent_uniqueness'][cluster_id]
            return "'{}': cluster {} ({:.2%} unique)".format(username, cluster_id + 1, uniqueness)
        else:
            return "no player '{}' in dataset".format(username)

    return ''


@app.callback(
    Output('tooltip', 'show'),
    Output('tooltip', 'bbox'),
    Output('tooltip', 'children'),
    Input('scatter-plot', 'hoverData'),
    State('split-dropdown', 'value'),
    State('skill-dropdown', 'value')
)
def update_tooltip(hover_data, split, skill):
    if hover_data is None:
        return False, no_update, no_update

    pt = hover_data['points'][0]
    bbox = pt['bbox']
    cluster_id = pt['pointNumber']
    size = clusters[split]['cluster_sizes'][cluster_id]

    children = [
        html.Div([
            html.Div(children=html.Strong("cluster {}".format(cluster_id + 1))),
            html.Div(children="{} players".format(size))
        ])
    ]
    return True, bbox, children

if __name__ == '__main__':
    app.run_server(debug=True)
