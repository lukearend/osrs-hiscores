""" Top-level containers for front-end contents. """

import dash_bootstrap_components as dbc
from dash import html

from app.components.blobs import username_blobs
from app.components.boxplot import boxplot
from app.components.dropdowns import split_menu, point_size_menu, color_by_menu
from app.components.input import username_input
from app.components.playertxt import focused_player
from app.components.slider import level_range_slider
from app.components.scatterplot import scatterplot
from app.components.space import vspace, vspace_if_nonempty
from app.components.table import player_stats_table, cluster_stats_table
from app.components.texts import page_title, info_blurb, github_link, download_link, support_msg
from app.layout import (
    DROPDOWN_WIDTHS,
    LOOKUP_SECTION_LAYOUT,
    TABLE_SECTION_LAYOUT,
    BOXPLOT_SECTION_LAYOUT,
    SCATTER_SECTION_LAYOUT,
)


def header():
    return dbc.Col([
        page_title(),
        info_blurb(),
        vspace(),
    ])


def footer():
    return dbc.Col([
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
        vspace(),
    ])


def tables():
    return dbc.Col([
        dbc.Row([
            player_stats_table(),
            cluster_stats_table(),
        ]),
        vspace(),
    ])


def controls():
    return dbc.Row(
        [
            dbc.Row([
                dbc.Col(
                    split_menu(),
                    **DROPDOWN_WIDTHS,
                ),
                dbc.Col(
                    point_size_menu(),
                    **DROPDOWN_WIDTHS,
                ),
                dbc.Col(
                    color_by_menu(),
                    **DROPDOWN_WIDTHS,
                ),
            ]),
            dbc.Col(
                level_range_slider(),
                width=12,
            ),
        ],
    )


def scatter():
    return dbc.Col([
        controls(),
        scatterplot(),
        vspace(),
    ])


def body():
    return dbc.Row([
        dbc.Col(
            [
                dbc.Col(
                    lookup(),
                    xs=dict(order=1),
                    lg=dict(order=1)
                ),
                dbc.Col(
                    tables(),
                    xs=dict(order=2),
                    lg=dict(order=3)
                ),
                dbc.Col(
                    boxplot(),
                    xs=dict(order=4),
                    lg=dict(order=4)
                ),
            ],
            xs=dict(size=12),
            lg=dict(size=6)
        ),
        dbc.Col(
            dbc.Col(
                scatter(),
                xs=dict(order=3),
                lg=dict(order=2),
            ),
            xs=dict(size=12),
            lg=dict(size=6)
        )
    ])
