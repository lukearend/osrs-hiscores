from typing import Any, Dict

import dash_bootstrap_components as dbc
from dash import Output, Input, dcc, html

from app import app, appdb
from app.helpers import is_valid_username
from src.common import osrs_skills


def store_vars():
    storevars = [
        dcc.Store('input-username'),
        dcc.Store('query-result')
    ]

    containers = []
    for var in storevars:
        containers.append(html.Div(id=f'container:{var.id}'))

        @app.callback(
            Output(f'container:{var.id}', 'children'),
            Input(var.id, 'data'),
        )
        def update_container(newval: Any) -> str:
            return str(newval)

    return dbc.Row([
        dbc.Col(
            [
                dbc.Row([
                    html.Div(f'{var.id}: '),
                    html.Div(id=f'container:{var.id}'),
                    var,
                ])
            ],
            width='auto'
        ) for var in storevars
    ])


@app.callback(
    Output('query-result', 'data'),
    Input('input-username', 'data'),
    prevent_initial_call=True,
)
def query_player(uname: str) -> Dict[str, Any]:
    if not is_valid_username(uname):
        return 'invalid'

    doc = appdb.find_one({'_id': uname.lower()})
    if not doc:
        return 'not found'

    skills = osrs_skills(include_total=True)
    stats = {skill: lvl for skill, lvl in zip(skills, doc['stats'])}
    return {
        'username': doc['username'],
        'cluster_ids': doc['clusterids'],
        'stats': stats,
    }
