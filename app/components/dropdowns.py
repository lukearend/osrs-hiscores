import collections
from typing import OrderedDict

import dash_bootstrap_components as dbc
from dash import Input, Output, html, callback_context

from app import app, appdata, styles
from app.helpers import get_trigger


def dropdown_menu(store_id: str, options: OrderedDict[str, str]):
    menuid = f'{store_id}:dropdown'

    menuitems = []
    for optid, label in options.items():
        button = dbc.DropdownMenuItem(label, id=f'{menuid}:{optid}')
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
            'cb': "combat skills only",
            'noncb': "non-combat skills only",
        }[split]
        optlabels[split] = label

    dropdown = dropdown_menu(
        store_id='current-split',
        options=optlabels,
    )
    label = html.Div("Choose split:", className='label-text')

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
    label = html.Div("Point size:", style={'font-weight': 'bold'})

    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(dropdown),
        ],
        align='center',
    )


def dropdown_menus():
    return dbc.Row(
        [
            dbc.Col(split_menu(), width='auto'),
            dbc.Col(point_size_menu(), width='auto'),
        ],
        className='g-5',  # g-4 is default, add a little separation
    )
