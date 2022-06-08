from typing import List

from dash import Output, Input, ALL, callback_context
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from app import app
from app.colors import HALO_COLORS as blob_colors
from app.helpers import triggered_id


def username_blobs():
    return dbc.Row(id='blob-container')


@app.callback(
    Output('blob-container', 'children'),
    Input('username-list', 'data'),
)
def draw_blobs(unames):
    blobs = [
        dbc.Button(
            uname,
            id={
                'type': 'blob',
                'username': uname,
            },
            style={
                'background-color': blob_colors[i % len(blob_colors)],
                'border-radius': '1em',
                'padding-left': '0.5em',
                'padding-right': '0.5em',
            }
        ) for i, uname in enumerate(unames)
    ]
    return [
        dbc.Col(
            blob,
            width='auto',
        ) for blob in blobs
    ]


@app.callback(
    Output('username-to-remove', 'data'),
    Input({'type': 'blob', 'username': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def handle_blob_click(_):
    trigger = triggered_id(callback_context)
    n_clicks = callback_context.triggered[0]['value']
    if n_clicks is None:
        raise PreventUpdate
    return trigger['username']
