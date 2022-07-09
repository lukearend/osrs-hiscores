import collections
from typing import OrderedDict

import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import Input, Output, html, callback_context

from app import app, appdata, styles
from app.helpers import get_trigger
from src.common import osrs_skills
from app.components.space import vspace


def dropdown_menu(store_id: str, options: OrderedDict[str, str]):
    menuid = f'{store_id}:dropdown'

    menuitems = []
    for optid, label in options.items():
        button = dbc.DropdownMenuItem(
            label,
            id=f'{menuid}:{optid}',
            className='controls-text'
        )
        menuitems.append(button)

    @app.callback(
        Output(store_id, 'data'),
        *[Input(button, 'n_clicks') for button in menuitems],
    )
    def select_menu_item(*args) -> str:
        buttonid, _ = get_trigger(callback_context)
        if buttonid is None:
            optids = list(options.keys())
            return optids[0]

        optid = buttonid.split(':')[2]
        return optid

    @app.callback(
        Output(menuid, 'label'),
        Input(store_id, 'data'),
    )
    def update_label(buttonid: str) -> str:
        return options[buttonid]

    return dbc.DropdownMenu(
        menuitems,
        id=f'{store_id}:dropdown',
        menu_variant=styles.MENU_VARIANT,
    )


def split_menu():
    splits = appdata.keys()
    optlabels = collections.OrderedDict()
    for split in splits:
        label = {
            'all': "all skills",
            'cb': "combat skills",
            'noncb': "non-combat skills",
        }[split]
        optlabels[split] = label

    dropdown = dropdown_menu(
        store_id='current-split',
        options=optlabels,
    )
    label = html.Strong(
        "Choose split:",
        className='controls-text'
    )
    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(dropdown),
        ],
        align='center',
    )


def point_size_menu():
    opts = ['small', 'medium', 'large']
    optlabels = collections.OrderedDict(zip(opts, opts))
    dropdown = dropdown_menu(
        store_id='point-size',
        options=optlabels,
    )
    label = html.Strong(
        "Point size:",
        className='controls-text',
    )
    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(dropdown),
        ],
        align='center',
    )


def color_by_menu():
    skills = osrs_skills(include_total=True)
    # optlabels = collections.OrderedDict([
    #     (skill, f'{skill.capitalize()} level')
    #     for skill in skills
    # ])
    optlabels = collections.OrderedDict(zip(skills, skills))
    dropdown = dropdown_menu(
        store_id='color-by-skill',
        options=optlabels,
    )
    label = html.Strong(
        "Color by:",
        className='controls-text',
    )
    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(dropdown),
        ],
        align='center',
    )


def level_range_slider():
    ticks = [500, 750, 1000, 1250, 1500, 1750, 2000, 2277]
    slider = dcc.RangeSlider(
        id='level-range-slider',
        step=1,
        min=500,
        max=2277,
        value=[500, 2277],
        marks={n: str(n) for n in ticks},
        allowCross=False,
        tooltip=dict(
            placement='bottom'
        ),
    )
    label = html.Strong(
        "Show levels:",
        className='controls-text',
    )
    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col([
                vspace(),  # vertically aligns slider bar with label text
                slider,
            ]),
        ],
        align='center',
        className='g-0',
    )


def scatterplot_controls():
    row1 = dbc.Row(
        [
            dbc.Col(split_menu(), width='auto'),
            dbc.Col(point_size_menu(), width='auto'),
        ],
    )
    row2 = dbc.Row(
        [
            dbc.Col(color_by_menu(), width='auto'),
            dbc.Col(level_range_slider())
        ],
        align='center',
    )
    return dbc.Col([
        row1,
        vspace(),
        row2,
    ])
