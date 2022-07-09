import collections
from typing import OrderedDict, List

import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import State, Input, Output, html, callback_context, no_update

from app import app, appdata, styles
from app.helpers import get_trigger
from app.components.space import vspace
from src.common import osrs_skills


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
    store_id = 'color-by-skill'
    skills = osrs_skills(include_total=True)

    menuitems = collections.OrderedDict()
    for skill in skills:
        menuitems[skill] = dbc.DropdownMenuItem(
            skill,
            id=f'{store_id}:dropdown:{skill}',
            className='controls-text'
        )

    @app.callback(
        Output(store_id, 'data'),
        Input('current-split', 'data'),
        *[Input(f'{store_id}:dropdown:{skill}', 'n_clicks') for skill in skills],
        State(store_id, 'data'),
        suppress_callback_exceptions=True,  # suppress error for conecting to component not (yet) in layout
    )
    def select_menu_item(*args) -> str:
        split = args[0]
        current_skill = args[-1]
        triggerid, _ = get_trigger(callback_context)

        new_skill = no_update
        if triggerid == 'current-split':
            split_skills = ['total'] + appdata[split].skills
            if current_skill not in split_skills:
                new_skill = 'total'
        else:
            new_skill = triggerid.split(':')[2]

        return new_skill

    @app.callback(
        Output(f'{store_id}:dropdown', 'label'),
        Input(store_id, 'data'),
    )
    def update_label(skill: str) -> str:
        return skill

    @app.callback(
        Output(f'{store_id}:dropdown', 'children'),
        Input('current-split', 'data'),
    )
    def update_menu_items(split) -> List[dbc.DropdownMenuItem]:
        new_skills = ['total'] + appdata[split].skills
        return [menuitems[s] for s in new_skills]

    dropdown = dbc.DropdownMenu(
        list(menuitems.values()),
        id=f'{store_id}:dropdown',
        menu_variant=styles.MENU_VARIANT,
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

    @app.callback(
        Output('level-range-slider', 'children'),
        Input('color-by-skill', 'data'),
    )
    def redraw_slider(skill: str) -> dbc.Col:
        if skill == 'total':
            ticks = [500, 750, 1000, 1250, 1500, 1750, 2000, 2277]
            minmax = [500, 2277]
        else:
            ticks = [1, 20, 40, 60, 80, 99]
            minmax = [1, 99]

        slider = dcc.RangeSlider(
            step=1,
            min=minmax[0],
            max=minmax[1],
            value=minmax,
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

    return dbc.Col(id='level-range-slider')


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
