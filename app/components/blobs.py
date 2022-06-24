
from dash import Output, Input, ALL, callback_context, no_update
import dash_bootstrap_components as dbc

from app import app
from app.styles import PLAYER_COLOR_SEQ as blob_colors
from app.helpers import get_trigger


def username_blobs():
    return dbc.Row(id='blob-container')


@app.callback(
    Output('blob-container', 'children'),
    Input('username-list', 'data'),
)
def draw_blobs(unames):
    blobs = []
    for i, uname in enumerate(unames):
        color = blob_colors[i % len(blob_colors)]

        blob_closer = dbc.Button(
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

        blob_content = dbc.Row(
            [
                dbc.Col(uname),
                blob_closer,
            ],
            className='g-2',  # decrease slightly, default is g-4
            align='center',
        )

        blob = dbc.Button(
            blob_content,
            id={
                'type': 'blob-username',
                'username': uname,
            },
            style={
                'background-color': color,
            },
            className='username-blob'
        )
        blobs.append(blob)

    return [dbc.Col(blob, width='auto') for blob in blobs]


@app.callback(
    Output('last-clicked-blob', 'data'),
    Input({'type': 'blob-username', 'username': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def handle_blob_click(_) -> str:
    return _clicked_username(callback_context)


@app.callback(
    Output('last-closed-username', 'data'),
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
