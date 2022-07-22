from typing import List, Any

import dash_bootstrap_components as dbc
from dash import Output, Input

from app import app
from app.backend import STORE_VARS

def store(show_inds: List[int] = None):
    if show_inds is None:
        return dbc.Col([v for v in STORE_VARS])

    show_ids = [v.id for i, v in STORE_VARS if i in show_inds]
    containers = []
    for var_id in show_ids:
        container_id = f'{var_id}:container'

        @app.callback(
            Output(container_id, 'children'),
            Input(var_id, 'data')
        )
        def update_container(newval: Any) -> str:
            return str(newval)

        c = dbc.Row(
            [
                dbc.Col(var_id + ': ', width='auto'),
                dbc.Col(id=container_id)
            ],
            className='g-2'
        )
        containers.append(c)

    return dbc.Col([
        dbc.Col([v for v in STORE_VARS]),
        dbc.Row([
            dbc.Col(c, width='auto') for c in containers
        ])
    ])
