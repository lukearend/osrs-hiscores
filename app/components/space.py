from typing import Any

from dash import Output, Input, html
import dash_bootstrap_components as dbc

from app import app


def vspace(n=1) -> html.Div():
    vspace = []
    for i in range(n):
        vspace.append(html.Div(className='vspace'))
    return dbc.Col(vspace)


def vspace_if_nonempty(id: str, n=1) -> dbc.Col:
    containerid = f'{id}:vspace'

    @app.callback(
        Output(containerid, 'children'),
        Input(id, 'data'),
    )
    def toggle_break(value: Any):
        if not value:
            return []
        return [vspace(n=1)]

    return dbc.Col(id=containerid)
