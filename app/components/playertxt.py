from typing import Dict, Any, List
from dash import Output, Input, html, no_update, State
from app import app, appdata


def focused_player():
    return html.Div(id='focused-player-txt', className='controls-text')


@app.callback(
    Output('focused-player-txt', 'children'),
    Input('focused-player', 'data'),
    Input('current-split', 'data'),
    State('current-players', 'data')
)
def update_focused_player_txt(uname: str, split: str,
                              player_list: List[Dict[str, Any]]) -> str:
    if not uname:
        return ''

    for p in player_list:
        if p['username'] == uname:
            player = p
            break
    else:
        return no_update

    uname = player['username']
    id = player['clusterids'][split]
    size = appdata['all'].cluster_sizes[id]
    uniq = appdata['all'].cluster_uniqueness[id]
    return f"{uname}: cluster {id} ({size} players, {uniq:.1%} unique)"
