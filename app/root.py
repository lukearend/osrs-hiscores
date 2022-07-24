""" Base application container. """

import dash_bootstrap_components as dbc
from app.components.space import vspace
from app.components.store import store
from app.containers import frontmatter, body


def root_layout():
    root = [
        vspace(),
        frontmatter(),
        vspace(),
        body(),
        vspace(),
        store()
    ]
    return dbc.Container([
        dbc.Row(dbc.Col(obj)) for obj in root
    ])
