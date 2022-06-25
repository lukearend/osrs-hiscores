import dash_bootstrap_components as dbc
from dash import html, dcc, Output, Input, no_update

from app import app, appdb
from app.helpers import is_valid_username, mongodoc_to_player


def username_input():
    label = html.Strong(
        'Lookup username:',
        className='controls-text',
    )
    inputbox = dcc.Input(
        # 'snakeylime',  # todo: remove after testing
        id='input-box',
        type='text',
        placeholder="e.g. 'snakeylime'",
        maxLength=12,
        debounce=True,  # don't trigger on every keystroke
        className='input-box controls-text',
    )
    querytxt = html.Div(
        id='query-text',
        className='query-text',
    )

    lookup = dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(inputbox),
        ],
        align='center',
    ),
    return dbc.Col(
        [
            dbc.Col(lookup),
            dbc.Col(querytxt),
        ],
        align='center',
    )


@app.callback(
    Output('query-text', 'children'),
    Output('last-queried-player', 'data'),
    Input('input-box', 'value'),
)
def handle_username_input(input_txt: str) -> str:
    if not input_txt:
        return '', no_update

    if not is_valid_username(input_txt):
        return f"'{input_txt}' is not a valid OSRS username", no_update

    doc = appdb.find_one({'_id': input_txt.lower()})
    if not doc:
        return f"player '{input_txt}' not found in dataset", no_update
    return '', mongodoc_to_player(doc)
