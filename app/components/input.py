from dataclasses import dataclass
from typing import Dict, List

from dash import html, dcc, Output, Input, State, no_update, callback_context, MATCH
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from app import app, appdb, appdata
from app.helpers import is_valid_username
from src.common import osrs_skills

from app.colors import HALO_COLORS


@dataclass
class PlayerData():
    """ Stats and cluster data for a player. """

    username: str
    stats: Dict[str, int]  # level in each skill (includes 'total')
    clusterids: Dict[str, int]  # cluster ID for each split of the dataset


def mongo_query_player(username: str) -> PlayerData:
    doc = appdb.find_one({'_id': username.lower()})
    if not doc:
        return None

    skills = osrs_skills(include_total=True)
    stats_list = doc['stats']
    stats = dict(zip(skills, stats_list))

    return PlayerData(
        username=doc['username'],
        clusterids=doc['clusterids'],
        stats=stats,
    )


class UsernameBlob():
    """ Blob displaying a username which can be clicked closed. """

    def __init__(self, username, index=0):
        self.color = HALO_COLORS[index % len(HALO_COLORS)]
        self.username = username
        self.closer = dbc.Button(id='blob-closer', className='btn-close', style={'background-color': self.color})

    def layout(self):
        return dbc.Col(
            dbc.Row(
                [
                    dbc.Col(
                        self.username,
                        width='auto',
                        align='center',
                    ),
                    dbc.Col(
                        self.closer,
                        align='center',
                    ),
                ],
                align='center',
            ),
            width='auto',
            className='username-blob',
            style={'background-color': self.color},
        )


class UsernameInput():
    """ Input field for username queries. """

    LABEL_TXT = 'Lookup username:'
    PROMPT = "e.g. 'snakeylime'"
    INVALID_UNAME_MSG = "'{}' is not a valid OSRS username"
    UNAME_NOT_FOUND_MSG = "player '{}' not found in dataset"
    QUERY_RESULT_MSG = "'{}': cluster {} ({} players, {:.1%} unique)"

    def __init__(self):
        self.label = html.Div(
            self.LABEL_TXT,
            className='label-text',
        )

        self.input_box = dcc.Input(
            id='username-search-box',
            type='text',
            placeholder=self.PROMPT,
            className='username-search-box',
            maxLength=12,
            debounce=True,  # don't trigger on every keystroke
        )

        self.query_result = html.Div(
            id='query-result',
        )

        self.usernames_container = dbc.Row(
            id='blobs-container',
        )

        self.username_to_add = dcc.Store('username-to-add')
        self.current_usernames = dcc.Store('displayed-usernames', data=[])

        @app.callback(
            Output('username-search-box', 'value'),
            Output('query-result', 'children'),
            Output('username-to-add', 'data'),
            Input('username-search-box', 'value'),
        )
        def query_username(queried_uname: str):
            if queried_uname is None:
                raise PreventUpdate

            if not is_valid_username(queried_uname):
                query_result = self.INVALID_UNAME_MSG.format(queried_uname)
                return no_update, query_result, no_update

            player = mongo_query_player(queried_uname)
            if not player:
                query_result = self.UNAME_NOT_FOUND_MSG.format(queried_uname)
                return no_update, query_result, no_update

            clusterid = player.clusterids['all']
            nplayers = appdata['all'].cluster_sizes[clusterid]
            uniqueness = appdata['all'].cluster_uniqueness[clusterid]
            query_result = self.QUERY_RESULT_MSG.format(player.username, clusterid, nplayers, uniqueness)

            return '', query_result, player.username

        @app.callback(
            Output('displayed-usernames', 'data'),
            Input('username-to-add', 'data'),
            State('displayed-usernames', 'data'),
        )
        def update_usernames(new_uname: str, current_unames: List[str]):
            if new_uname is None:
                raise PreventUpdate
            if new_uname in current_unames:
                current_unames.remove(new_uname)
            current_unames.append(new_uname)
            return current_unames

        @app.callback(
            Output('blobs-container', 'children'),
            Input('displayed-usernames', 'data'),
        )
        def update_blobs(usernames: List[str]):
            blobs = [UsernameBlob(uname, index=i) for i, uname in enumerate(usernames)]
            return dbc.Row([b.layout() for b in blobs])

        @app.callback(
            Output('blob-container', 'children'),
            Input('blob-closer', 'n_clicks'),
        )
        def test_button(n_clicks):
            print(f'n_clicks: {n_clicks}')
            if n_clicks is None:
                raise PreventUpdate
            return 'button closed'

    def layout(self):
        lookup_box = dbc.Row(
            [
                dbc.Col(self.label, width='auto'),
                dbc.Col(self.input_box),
            ],
            align='center',
        )
        top_row = dbc.Row([
            dbc.Col(lookup_box, width='auto'),
            dbc.Col(self.query_result),
        ])
        store = dbc.Col([
            self.username_to_add,
            self.current_usernames,
        ])
        return dbc.Col([
            top_row,
            html.Br(),
            self.usernames_container,
            store,
            html.Div(id='blob-container')
        ])
