from typing import Any

from dash import Output, Input, html
import dash_bootstrap_components as dbc

from app import app


def vspace() -> html.Div():
    return html.Div(className='vspace')


def vspace_if_nonempty(id: str) -> dbc.Col:
    containerid = f'{id}:vspace'

    @app.callback(
        Output(containerid, 'children'),
        Input(id, 'data'),
    )
    def toggle_break(value: Any):
        if not value:
            return []
        return [vspace()]

    return dbc.Col(id=containerid)
