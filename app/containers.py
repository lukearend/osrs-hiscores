""" Top-level containers which compose the front end. """

from typing import Any, List

import dash_bootstrap_components as dbc
from dash import html, Output, Input

from app import app
from app.components.blobs import username_blobs
from app.components.boxplot import boxplot as boxplot_fig
from app.components.dropdowns import split_menu, point_size_menu, color_by_menu
from app.components.input import username_input
from app.components.playertxt import focused_player
from app.components.scatterplot import scatterplot as scatterplot_fig
from app.components.slider import level_range_slider
from app.components.space import vspace, vspace_if_nonempty
from app.components.table import player_stats_table, cluster_stats_table
from app.components.texts import page_title, info_blurb, github_link, download_link, support_msg
from app.backend import STORE


def header():
    return dbc.Col([
        vspace(),
        page_title(),
        info_blurb(),
        vspace(),
    ])


def footer():
    return dbc.Col([
        vspace(),
        github_link(),
        download_link(),
        html.Hr(),
        support_msg(),
        vspace(),
    ])


def lookup():
    return dbc.Col([
        username_input(),
        vspace(),
        username_blobs(),
        vspace_if_nonempty(id='current-players'),
        focused_player(),
        vspace_if_nonempty(id='focused-player'),
    ])


def controls():
    dropdown1 = split_menu()
    dropdown2 = point_size_menu()
    dropdown3 = color_by_menu()
    slider = level_range_slider()

    row1 = dbc.Row([
        dbc.Col(
            dropdown1,
            width='auto',
        ),
        dbc.Col(dropdown2),
    ])

    row2 = dbc.Row(
        [
            dbc.Col(
                dropdown3,
                width='auto',
            ),
            dbc.Col(slider),
        ],
        align='center',
    )

    return dbc.Col([
        row1,
        row2,
    ])


def scatterplot():
    return dbc.Col([
        scatterplot_fig(),
        vspace(),
    ])


def tables():
    table_row = dbc.Row(
        [
            dbc.Col(
                player_stats_table(),
                width=6,
            ),
            dbc.Col(
                cluster_stats_table(),
                width=6,
            ),
        ],
    )
    return dbc.Col([
        table_row,
        vspace(),
    ])


def boxplot():
    return dbc.Col([
        boxplot_fig(),
        vspace(),
    ])


def store(show_inds: List[int] = None):
    if show_inds is None:
        return dbc.Col([v for v in STORE])

    show_ids = [v.id for i, v in STORE if i in show_inds]
    containers = []
    for var_id in show_ids:
        container_id = f'{var_id}:container'

        @app.callback(
            Output(container_id, 'children'),
            Input(var_id, 'data'),
        )
        def update_container(newval: Any) -> str:
            return str(newval)

        c = dbc.Row(
            [
                dbc.Col(var_id + ': ', width='auto'),
                dbc.Col(id=container_id),
            ],
            className='g-2',
        )
        containers.append(c)

    return dbc.Col([
        dbc.Col([v for v in STORE]),
        dbc.Row([
            dbc.Col(
                c,
                width='auto',
            ) for c in containers
        ])
    ])
