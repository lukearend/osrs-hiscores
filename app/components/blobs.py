""" Clickable blobs displaying the current users. """

from dash import Output, Input, ALL, callback_context, no_update
import dash_bootstrap_components as dbc

from app import app
from app.helpers import get_trigger


def username_blobs():
    return dbc.Row(id='blob-container')


@app.callback(
    Output('blob-container', 'children'),
    Input('current-players', 'data'),
)
def draw_blobs(players):
    blobs = []

    for i, p in enumerate(players):
        uname = p['username']
        color = p['color']

        blob_x = dbc.Button(
            className='btn-close',
            id={
                'type': 'blob-x',
                'username': uname,
            },
            style={
                'background-color': color,
                'font-size': 'small',
            },
        )
        blob = dbc.Row(
            [
                dbc.Col(uname),
                blob_x,
            ],
            className='g-2',  # decrease slightly, default is g-4
            align='center',
        )
        blob_btn = dbc.Button(
            blob,
            id={
                'type': 'blob-username',
                'username': uname,
            },
            style={
                'background-color': color,
            },
            className='username-blob'
        )

        blobs.append(blob_btn)

    return [dbc.Col(blob, width='auto') for blob in blobs]


@app.callback(
    Output('clicked-blob', 'data'),
    Input({'type': 'blob-username', 'username': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def handle_blob_click(_) -> str:
    return _clicked_username(callback_context)


@app.callback(
    Output('closed-blob', 'data'),
    Input({'type': 'blob-x', 'username': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def handle_blob_close(_) -> str:
    return _clicked_username(callback_context)


def _clicked_username(ctx) -> str:
    triggerid, nclicks = get_trigger(ctx)
    if triggerid is None or nclicks is None:
        return no_update
    return triggerid['username']
