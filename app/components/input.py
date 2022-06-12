from typing import Dict

import dash_bootstrap_components as dbc
from dash import html, dcc, State, Output, Input, callback_context, no_update
from dash.exceptions import PreventUpdate

from app import app, appdb, appdata
from app.helpers import is_valid_username, mongodoc_to_player


def username_input():
    label = html.Div('Lookup username:', className='label-text')
    querytxt = html.Div(id='query-text')
    inputbox = dcc.Input(
        id='input-box',
        type='text',
        placeholder="e.g. 'snakeylime'",
        maxLength=12,
        debounce=True,  # don't trigger on every keystroke
        className='input-box',
    )
    lookup = dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(inputbox),
        ],
        align='center',
    ),
    return dbc.Row([
        dbc.Col(lookup, width='auto'),
        dbc.Col(querytxt),
    ])


@app.callback(
    Output('query-text', 'children'),
    Output('last-queried-player', 'data'),
    Input('input-box', 'value'),
    State('current-split', 'data'),
)
def handle_username_input(input_txt: str, split: str) -> str:
    if not callback_context.triggered:
        return '', no_update

    if input_txt == '':
        raise PreventUpdate

    if not is_valid_username(input_txt):
        return f"'{input_txt}' is not a valid OSRS username", no_update

    doc = appdb.find_one({'_id': input_txt.lower()})
    if not doc:
        return f"player '{input_txt}' not found in dataset", no_update

    player = mongodoc_to_player(doc)

    uname = player['username']
    id = player['clusterids'][split]
    size = appdata['all'].cluster_sizes[id]
    uniq = appdata['all'].cluster_uniqueness[id]
    querytxt = f"'{uname}': cluster {id} ({size} players, {uniq:.1%} unique)"

    return querytxt, player
