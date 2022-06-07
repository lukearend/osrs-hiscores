from dataclasses import dataclass
from typing import Dict, List

from dash import html, dcc, Output, Input, State, no_update, callback_context, MATCH
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from app import app, appdb, appdata
from app.helpers import is_valid_username
from src.common import osrs_skills

from app.colors import HALO_COLORS


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


class BlobContainer():
    pass
