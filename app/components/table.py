import dash_bootstrap_components as dbc
from dash import html, State, Output, Input

from app import app, appdata
from src.common import osrs_skills


OSRS_SKILLS = osrs_skills(include_total=True)


def stats_table(id):

    # @app.callback(
    #     Output('', ''),
    #     Input('', ''),
    #     State('current-split', ''),
    # )
    # def update_table():
    #     pass

    return html.Div(id)


def cluster_stats_table():
    title = html.Div("Cluster averages")
    table = stats_table('cluster-stats-table')
    return dbc.Col([
        title,
        table
    ])


def player_stats_table():
    title = html.Div("Player stats")
    table = stats_table('player-stats-table')
    return dbc.Col([
        title,
        table
    ])


def stats_tables():
    return dbc.Row([
        dbc.Col(player_stats_table(), width='auto'),
        dbc.Col(cluster_stats_table()),
    ])
