import collections
from typing import OrderedDict, List, Dict

import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import State, Input, Output, html, callback_context, no_update

from app import app, appdata, styles
from app.helpers import get_trigger


def generic_dropdown(id: str, store_var: str, label_var: str,
                     options: OrderedDict[str, str]) -> dbc.DropdownMenu:

    btns = []
    for opt_id, opt_label in options.items():
        b = dbc.DropdownMenuItem(
            opt_label,
            id=f'{id}:{opt_id}',
            className='controls-text'
        )
        btns.append(b)

    @app.callback(
        Output(store_var, 'data'),
        *[Input(f'{id}:{opt_id}', 'n_clicks') for opt_id in options.keys()]
    )
    def select_menu_item(*args) -> str:
        btn_id, _ = get_trigger(callback_context)
        if btn_id is None:
            return list(options.keys())[0]
        return btn_id.split(':')[-1]

    @app.callback(
        Output(id, 'label'),
        Input(label_var, 'data'),
    )
    def update_label(opt: str) -> str:
        if opt not in options:
            return no_update
        return options[opt]

    return dbc.DropdownMenu(
        btns,
        id=id,
        menu_variant=styles.MENU_VARIANT,
    )


def split_menu():
    opts = collections.OrderedDict()
    for split in appdata.keys():
        opt_label = {
            'all': "all skills",
            'cb': "combat skills",
            'noncb': "non-combat skills",
        }[split]
        opts[split] = opt_label

    dropdown = generic_dropdown(
        id='current-split:dropdown',
        store_var='current-split',
        label_var='current-split',
        options=opts,
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
    dropdown = generic_dropdown(
        id='point-size:dropdown',
        store_var='point-size',
        label_var='point-size',
        options=collections.OrderedDict(zip(opts, opts)),
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
    splits = appdata.keys()

    # Pre-create dropdowns with different options for each of the different splits.
    menus = []
    vars = []
    for split in splits:
        skills = ['total'] + appdata[split].skills
        menu = generic_dropdown(
            id=f'color-by-skill:{split}:dropdown',
            store_var=f'color-by-skill:{split}',
            label_var='color-by-skill',
            options= collections.OrderedDict(zip(skills, skills)),
        )
        var = dcc.Store(f'color-by-skill:{split}')
        menus.append(menu)
        vars.append(var)

    # Update a shared store var when any of their individual store vars changes.
    @app.callback(
        Output('color-by-skill', 'data'),
        *[Input(f'color-by-skill:{split}', 'data') for split in splits],
        Input('current-split', 'data'),
        State('color-by-skill', 'data'),
    )
    def update_current_skill(*args) -> str:
        split: str = args[-2]
        current_skill: str = args[-1]

        trigger, val = get_trigger(callback_context)
        if trigger != 'current-split':
            return val
        elif current_skill not in appdata[split].skills:
            return 'total'
        return no_update

    # Only the dropdown for the current split is visible.
    @app.callback(
        *[Output(f'color-by-skill:{split}:dropdown', 'style') for split in splits],
        Input('current-split', 'data'),
    )
    def update_visibility(new_split) -> List[Dict[str, str]]:
        visible = [True if split == new_split else False for split in splits]
        return [{'display': 'inline' if v else 'none'} for v in visible]

    label = html.Strong(
        "Color by:",
        className='controls-text',
    )
    return dbc.Row(
        [
            *vars,
            dbc.Col(label, width='auto'),
            dbc.Col(menus),
        ],
        align='center',
    )
