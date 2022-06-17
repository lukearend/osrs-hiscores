from typing import Any, List, Dict, Tuple

import dash_bootstrap_components as dbc
from dash import Output, Input, dcc, State, callback_context, no_update

from app import app, appdata
from app.helpers import get_trigger


def store_vars():
    storevars = [
        dcc.Store('username-list', data=[]),
        dcc.Store('player-data-dict', data={}),
        dcc.Store('focused-player'),        # Dict[str, Any]
        dcc.Store('current-clusterid'),     # int
        dcc.Store('current-split'),         # str
        dcc.Store('point-size'),            # str
        dcc.Store('scatterplot-data'),      # Dict[str, Any]
        dcc.Store('boxplot-data'),          # Dict[str, Any]
        dcc.Store('cluster-table-data'),    # Dict[str, int]
        dcc.Store('player-table-data'),     # Dict[str, int]
        dcc.Store('last-queried-player'),   # Dict[str, Any]
        dcc.Store('last-closed-username'),  # str
        dcc.Store('last-clicked-blob'),     # str
    ]

    children = []
    for var in storevars:
        containerid = f'{var.id}:container'

        container = dbc.Row(
            [
                var,
                dbc.Col(var.id + ': ', width='auto'),
                dbc.Col(id=containerid),
            ],
            className='g-2',
        )
        children.append(container)

        @app.callback(
            Output(containerid, 'children'),
            Input(var.id, 'data'),
        )
        def update_value(newval: Any) -> str:
            return str(newval)

    return dbc.Row([
        dbc.Col(
            storevar,
            width='auto',
        )
        for storevar in children
    ])


@app.callback(
    Output('username-list', 'data'),
    Output('player-data-dict', 'data'),
    Input('last-queried-player', 'data'),
    Input('last-closed-username', 'data'),
    State('username-list', 'data'),
    State('player-data-dict', 'data'),
    prevent_initial_call=True,
)
def update_player_list(queried_player: Dict[str, Any],
                       closed_player: str,
                       uname_list: List[str],
                       data_dict: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:

    triggerid, _ = get_trigger(callback_context)
    if triggerid == 'last-queried-player':
        uname = queried_player['username']
        if uname in uname_list:
            uname_list.remove(uname)

        uname_list.append(uname)
        data_dict[uname] = queried_player

    elif triggerid == 'last-closed-username':
        uname_list.remove(closed_player)
        del data_dict[closed_player]

    return uname_list, data_dict


@app.callback(
    Output('focused-player', 'data'),
    Input('last-clicked-blob', 'data'),
    Input('last-queried-player', 'data'),
    Input('last-closed-username', 'data'),
    State('focused-player', 'data'),
    State('player-data-dict', 'data'),
    prevent_initial_call=True,
)
def updated_focused_player(blob_uname: str,
                           player_query: Dict[str, Any],
                           closed_uname: str,
                           current_player: Dict[str, Any],
                           data_dict: Dict[str, Any]) -> Dict[str, Any]:

    triggerid, _ = get_trigger(callback_context)
    if triggerid == 'last-clicked-blob':
        return data_dict[blob_uname]
    if triggerid == 'last-queried-player':
        return player_query
    if triggerid == 'last-closed-username':
        if current_player is None:
            return None
        if closed_uname == current_player['username']:
            return None
        return current_player

    return no_update


@app.callback(
    Output('current-clusterid', 'data'),
    Input('focused-player', 'data'),
    Input('current-split', 'data'),
    State('player-data-dict', 'data'),
    prevent_initial_call=True,
)
def update_current_cluster(player: Dict[str, Any], split: str, data_dict: Dict[str, Any]) -> int:
    if player is None:
        return no_update

    uname = player['username']
    return data_dict[uname]['clusterids'][split]


@app.callback(
    Output('boxplot-data', 'data'),
    Input('current-clusterid', 'data'),
    Input('current-split', 'data'),
    prevent_initial_call=True,
)
def update_boxplot_data(clusterid: int, split: str) -> Dict[str, Any]:
    if clusterid is None:
        return no_update

    nplayers = appdata[split].cluster_sizes[clusterid].item()
    quartiles_xr = appdata[split].cluster_quartiles.sel(clusterid=clusterid)
    quartiles_xr = quartiles_xr.drop_sel(skill='total')
    skills = [s.item() for s in quartiles_xr.coords['skill']]

    boxdata = []
    for p in [0, 25, 50, 75, 100]:
        lvls = quartiles_xr.sel(percentile=p)
        lvls = [i.item() for i in lvls]
        skill_lvls = dict(zip(skills, lvls))
        boxdata.append(skill_lvls)

    return {
        'id': clusterid,
        'num_players': nplayers,
        'quartiles': boxdata
    }


@app.callback(
    Output('cluster-table-data', 'data'),
    Input('current-clusterid', 'data'),
    State('current-split', 'data'),
    prevent_initial_call=True,
)
def update_cluster_table_data(clusterid, split) -> Dict[str, int]:
    if clusterid is None:
        return no_update

    centroid = appdata[split].cluster_centroids.loc[clusterid]
    skills = centroid.index
    lvls = [int(i) for i in centroid]
    return dict(zip(skills, lvls))


@app.callback(
    Output('player-table-data', 'data'),
    Input('focused-player', 'data'),
    State('current-split', 'data'),
    prevent_initial_call = True,
)
def update_player_table_data(player, split) -> Dict[str, int]:
    if player is None:
        return no_update

    show_skills = appdata[split].skills
    show_skills.append('total')
    return {
        skill: lvl for skill, lvl in player['stats'].items()
        if skill in show_skills
    }
