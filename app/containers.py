""" Top-level containers for front-end contents. """

import dash_bootstrap_components as dbc

from app.components.blobs import username_blobs
from app.components.boxplot import boxplot
from app.components.dropdowns import split_menu, point_size_menu, color_by_menu
from app.components.input import username_input
from app.components.playertxt import focused_player
from app.components.slider import level_range_slider
from app.components.scatterplot import scatterplot
from app.components.space import vspace, vspace_if_nonempty
from app.components.table import player_stats_table, cluster_stats_table
from app.components.texts import page_title, info_blurb, top_buttons, watermark
from app.styles import (
    DROPDOWN_WIDTHS,
    LOOKUP_SECTION_LAYOUT,
    TABLE_SECTION_LAYOUT,
    BOXPLOT_SECTION_LAYOUT,
    SCATTER_SECTION_LAYOUT,
    WATERMARK_SECTION_LAYOUT,
    FLOATING_BREAK1_LAYOUT,
    FLOATING_BREAK2_LAYOUT
)


def frontmatter():
    return dbc.Col([
        top_buttons(),
        page_title(),
        info_blurb(),
        vspace()
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


def tables():
    return dbc.Col([
        dbc.Row([
            player_stats_table(),
            cluster_stats_table()
        ]),
        vspace()
    ])


def controls():
    return dbc.Row(
        [
            dbc.Row([
                dbc.Col(split_menu(), **DROPDOWN_WIDTHS),
                dbc.Col(point_size_menu(), **DROPDOWN_WIDTHS),
                dbc.Col(color_by_menu(), **DROPDOWN_WIDTHS)
            ]),
            dbc.Col(level_range_slider(), width=12)
        ]
    )


def scatter():
    return dbc.Col([
        controls(),
        scatterplot(),
    ])


def body():
    return dbc.Row([
        dbc.Col(lookup(), **LOOKUP_SECTION_LAYOUT),
        dbc.Col(tables(), **TABLE_SECTION_LAYOUT),
        dbc.Col(scatter(), **SCATTER_SECTION_LAYOUT),
        dbc.Col(vspace(), **FLOATING_BREAK1_LAYOUT),
        dbc.Col(boxplot(), **BOXPLOT_SECTION_LAYOUT),
        dbc.Col(vspace(), **FLOATING_BREAK2_LAYOUT),
        dbc.Col(watermark(), **WATERMARK_SECTION_LAYOUT),
    ],
    className='body-container'
)
