from dash import html, Dash, dcc
from pymongo.collection import Collection

from src.app.backend import DataStore


class UsernameInput:
    """ Input field for usernames to query. """

    def __init__(self, app: Dash, player_coll: Collection, datastore: DataStore):
        self.app = app
        self.coll = player_coll
        self.datastore = datastore

        self.label = html.Div('Lookup username:', style={'font-weight': 'bold'})
        self.input = dcc.Input(
            id='username-input',
            type='text',
            placeholder="e.g. 'snakeylime'",
            className='username-input'
        )

    def add_callbacks(self):
        pass
