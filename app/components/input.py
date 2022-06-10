from dash import html, dcc, Output, Input, callback_context, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from app import app, appdb, appdata
from app.helpers import is_valid_username


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
)
def handle_username_input(input_txt: str) -> str:
    if not callback_context.triggered:
        return '', no_update

    if input_txt == '':
        raise PreventUpdate

    if not is_valid_username(input_txt):
        return f"'{input_txt}' is not a valid OSRS username", no_update

    doc = appdb.find_one({'_id': input_txt.lower()})
    if not doc:
        return f"player '{input_txt}' not found in dataset", no_update

    uname = doc['username']
    id = doc['clusterids']['all']
    size = appdata['all'].cluster_sizes[id]
    uniq = appdata['all'].cluster_uniqueness[id]
    return f"'{uname}': cluster {id} ({size} players, {uniq:.1%} unique)", uname
