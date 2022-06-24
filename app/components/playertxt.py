from typing import Dict, Any

from dash import Output, Input, html

from app import app, appdata


def focused_player():
    return html.Div(
        id='focused-player-txt',
        className='controls-text',
    )


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
