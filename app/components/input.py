from app import app, appdb, appdata
from dash import html, dcc
import dash_bootstrap_components as dbc


def username_input_box():
    """ Input field for usernames to query. """

    label = html.Div(
        'Lookup username:',
        className='label-text',
    )
    input_box = dcc.Input(
        id='username-input',
        type='text',
        placeholder="e.g. 'snakeylime'",
        className='username-input',
    )
    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col(input_box),
        ],
        align='center',
    )


def current_usernames_box():
    """ Field containing currently queried usernames. """

    return dbc.Col()
