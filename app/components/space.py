""" Spacer elements """

from typing import Any

from dash import Output, Input, html
import dash_bootstrap_components as dbc

from app import app


def vspace(n=1) -> html.Div():
    spacers = []
    for i in range(n):
        spacers.append(html.Div(className='vspace'))
    return dbc.Col(spacers)


def vspace_if_nonempty(id: str) -> dbc.Col:
    container_id = f'{id}:vspace'

    @app.callback(
        Output(container_id, 'children'),
        Input(id, 'data')
    )
    def toggle_break(value: Any):
        if not value:
            return []
        return [vspace()]

    return dbc.Col(id=container_id)
