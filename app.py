#!/usr/bin/env python3

""" Visualize 3d-embedded cluster data with a Dash application. """

import pickle

import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.express as px
import pandas as pd


print('loading data...')

with open('data/processed/dimreduced.pkl', 'rb') as f:
    data = pickle.load(f)
with open('data/processed/centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)
with open('data/processed/clusters.pkl', 'rb') as f:
    clusters = pickle.load(f)

# Convert data into dataframe for plotting.
for split, xyz_data in data.items():

    num_clusters = len(xyz_data)
    total_levels = centroids[split][50][:, 0]
    cluster_sizes = clusters[split]['cluster_sizes']
    cluster_sizes = np.expand_dims(cluster_sizes, axis=1)

    data_array = np.concatenate([xyz_data, total_levels, 0.1 * cluster_sizes], axis=1)
    df = pd.DataFrame(data_array,
                      columns=('x', 'y', 'z', 'Total level', 'size'),
                      index=np.arange(1, num_clusters + 1))
    data[split] = df


# Create Plotly scatter plot from dataframe.
fig = px.scatter_3d(data['cb'], x='x', y='y', z='z',
                    color="Total level",
                    hover_data=['size'])


# Run Dash app displaying Plotly graphics.
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1(children='OSRS combat skill clusters'),

    html.Div(children='''
        Each point represents a cluster of OSRS players with similar combat
        stats. The closer two clusters are, the more similar are the accounts
        in each of those two clusters. Some clusters contain only a single
        (highly) unique player; others comprise thousands or tens of thousands
        of similar accounts. The size of each point corresponds to the number
        of players in that cluster. The clusters are color-coded by total
        level; axes have no meaningful units.
    '''),

    dcc.Graph(id="scatter-plot",
              figure=fig)
])


if __name__ == '__main__':
    app.run_server(debug=True)
