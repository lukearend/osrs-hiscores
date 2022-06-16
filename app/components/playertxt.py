from typing import List, Dict, Any

from dash import State, Output, Input, html
import dash_bootstrap_components as dbc

from app import app, appdata


def focused_player():
    info = html.Div(id='focused-player-txt')
    return dbc.Col(
        id='focused-player-container',
        children=[info]
    )


@app.callback(
    Output('focused-player-container', 'children'),
    Input('focused-player-txt', 'children'),
    State('focused-player-container', 'children'),
)
def toggle_section_br(new_playertxt: str, section_children: List) -> List:
    playertxt = section_children[0]
    if not new_playertxt:
        return [playertxt]
    return [playertxt, html.Br()]


@app.callback(
    Output('focused-player-txt', 'children'),
    Input('focused-player', 'data'),
    Input('current-split', 'data'),
)
def update_focused_player_txt(player: Dict[str, Any], split: str):
    if not player:
        return ''

    uname = player['username']
    id = player['clusterids'][split]
    size = appdata['all'].cluster_sizes[id]
    uniq = appdata['all'].cluster_uniqueness[id]
    return f"{uname}: cluster {id} ({size} players, {uniq:.1%} unique)"
