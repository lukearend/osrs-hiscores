from typing import Any, Dict

from dash import html, dcc, Output, Input, no_update, State
import dash_bootstrap_components as dbc

from app import app, appdata


def username_input():
    label = html.Div('Lookup username:', className='label-text')
    inputbox = dcc.Input(
        id='input-box',
        type='text',
        placeholder="e.g. 'snakeylime'",
        className='input-box',
        maxLength=12,
        debounce=True,  # don't trigger on every keystroke
    )
    querytxt = html.Div(id='query-text')
    return dbc.Row([
        dbc.Col(
            dbc.Row(
                [
                    dbc.Col(label, width='auto'),
                    dbc.Col(inputbox),
                ],
                align='center',
            ),
            width='auto'
        ),
        dbc.Col(querytxt),
    ])


@app.callback(
    Output('input-username', 'data'),
    Input('input-box', 'value'),
    prevent_initial_call=True,
)
def parse_username_input(input_txt: str) -> str:
    if not input_txt:
        return no_update
    return input_txt


@app.callback(
    Output('query-text', 'children'),
    Input('query-result', 'data'),
    State('input-username', 'data'),
)
def update_query_text(result: Dict[str, Any], uname: str) -> str:
    if result is None:
        return ''

    if result == 'invalid':
        return f"'{uname}' is not a valid OSRS username"

    if result == 'not found':
        return f"player '{uname}' not found in dataset"

    clusterid = result['cluster_ids']['all']
    return "'{}': cluster {} ({} players, {:.1%} unique)".format(
        result['username'],
        clusterid,
        appdata['all'].cluster_sizes[clusterid],
        appdata['all'].cluster_uniqueness[clusterid],
    )
