from typing import Any, List

import dash_bootstrap_components as dbc
from dash import Output, Input, dcc, State, callback_context, no_update, html

from app import app
from app.helpers import get_trigger


def store_vars():
    storevars = [
        dcc.Store('username-list', data=[]),
        dcc.Store('selected-username', data=None),
        dcc.Store('last-queried-player'),
        dcc.Store('last-closed-player'),
        dcc.Store('last-clicked-blob'),
    ]

    children = []
    for var in storevars:
        containerid = f'container:{var.id}'

        container = dbc.Row(
            [
                var,
                dbc.Col(var.id + ': ', width='auto'),
                dbc.Col(id=containerid),
            ],
            className='g-2',
        )
        children.append(container)

        @app.callback(
            Output(containerid, 'children'),
            Input(var.id, 'data'),
        )
        def update_value(newval: Any) -> str:
            return str(newval)

    return dbc.Row([
        dbc.Col(
            preview,
            width='auto',
        )
        for preview in children
    ])


@app.callback(
    Output('username-list', 'data'),
    Input('last-queried-player', 'data'),
    Input('last-closed-player', 'data'),
    State('username-list', 'data'),
)
def update_username_list(queried_player: str,
                         closed_player: str,
                         uname_list: List[str]):

    triggerid, uname = get_trigger(callback_context)
    if triggerid is None:
        return no_update

    elif triggerid == 'last-queried-player':
        if queried_player in uname_list:
            uname_list.remove(queried_player)
        uname_list.append(queried_player)

    elif triggerid == 'last-closed-player':
        uname_list.remove(closed_player)

    return uname_list


@app.callback(
    Output('selected-username', 'data'),
    Input('last-clicked-blob', 'data'),
    Input('last-queried-player', 'data'),
    Input('last-closed-player', 'data'),
    State('selected-username', 'data'),
)
def update_selected_username(clicked_blob: str,
                             queried_player: str,
                             closed_player: str,
                             current_uname: str):

    triggerid, uname = get_trigger(callback_context)
    if triggerid is None:
        return no_update

    elif triggerid == 'last-clicked-blob':
        current_uname = clicked_blob

    elif triggerid == 'last-queried-player':
        current_uname = queried_player

    elif triggerid == 'last-closed-player':
        if closed_player == current_uname:
            current_uname = None

    return current_uname


