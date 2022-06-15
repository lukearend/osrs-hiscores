import collections
from typing import OrderedDict

import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import Input, Output, html, callback_context

from app import app, appdata
from app.helpers import get_trigger


def dropdown_menu(store_id: str, options: OrderedDict[str, str]):
    menuitems = []
    for optid, label in options.items():
        button = dbc.DropdownMenuItem(label, id=f'{store_id}:dropdown:{optid}')
        menuitems.append(button)

    storevar = dcc.Store(store_id)
    menu = dbc.DropdownMenu(
        menuitems,
        id=f'{store_id}:dropdown',
        menu_variant='dark',
    )

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
        Output(menu, 'label'),
        Input(store_id, 'data'),
    )
    def update_label(buttonid: str) -> str:
        return options[buttonid]

    return dbc.Col([storevar, menu])


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
    return dbc.Row([
        dbc.Col(split_menu()),
        dbc.Col(point_size_menu()),
    ])
