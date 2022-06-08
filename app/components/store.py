from typing import Any, List

import dash_bootstrap_components as dbc
from dash import Output, Input, dcc, html, State, callback_context, no_update

from app import app
from app.helpers import triggered_id


def store_vars():
    storevars = [
        dcc.Store('username-list', data=[]),
        dcc.Store('username-to-append'),
        dcc.Store('username-to-remove'),
    ]

    children = []
    for var in storevars:
        containerid = f'container:{var.id}'

        container = dbc.Col(
            dbc.Row([
                html.Div(var.id + ': '),
                html.Div(id=containerid),
            ]),
            width='auto',
        )
        children.append(var)
        children.append(container)

        @app.callback(
            Output(containerid, 'children'),
            Input(var.id, 'data'),
        )
        def update_value(newval: Any) -> str:
            return str(newval)

    return dbc.Row(children)


@app.callback(
    Output('username-list', 'data'),
    Input('username-to-append', 'data'),
    Input('username-to-remove', 'data'),
    State('username-list', 'data'),
)
def update_username_list(add_uname: str, rm_uname: str, uname_list: List[str]):
    trigger = triggered_id(callback_context)
    if trigger is None:
        return no_update

    if trigger == 'username-to-append':
        if add_uname in uname_list:
            uname_list.remove(add_uname)
        uname_list.append(add_uname)
    else:
        uname_list.remove(rm_uname)

    return uname_list
