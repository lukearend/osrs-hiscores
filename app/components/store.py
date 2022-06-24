from typing import Any, List, Dict, Tuple

import dash_bootstrap_components as dbc
import numpy as np
from dash import Output, Input, dcc, State, callback_context, no_update

from app import app, appdata
from app.helpers import get_trigger
from src.common import osrs_skills


def store_vars(show=True):
    storevars = [
        dcc.Store('username-list', data=[]),
        dcc.Store('player-data-dict', data={}),
        dcc.Store('focused-player'),            # Dict[str, Any]
        dcc.Store('current-clusterid'),         # int
        dcc.Store('current-split'),             # str
        dcc.Store('point-size'),                # str
        dcc.Store('scatterplot-data'),          # Dict[str, Any]
        dcc.Store('boxplot-data'),              # Dict[str, Any]
        dcc.Store('cluster-table-data:title'),  # int
        dcc.Store('cluster-table-data:stats'),  # Dict[str, int]
        dcc.Store('player-table-data:title'),   # str
        dcc.Store('player-table-data:stats'),   # Dict[str, int]
        dcc.Store('last-queried-player'),       # Dict[str, Any]
        dcc.Store('last-closed-username'),      # str
        dcc.Store('last-clicked-blob'),         # str
    ]

    layout = []
    for var in storevars:
        if not show:
            layout.append(var)
            continue

        containerid = f'{var.id}:container'
        container = dbc.Row(
            [
                var,
                dbc.Col(var.id + ': ', width='auto'),
                dbc.Col(id=containerid),
            ],
            className='g-2',
        )
        layout.append(container)

        @app.callback(
            Output(containerid, 'children'),
            Input(var.id, 'data'),
        )
        def update_container(newval: Any) -> str:
            return str(newval)

    return dbc.Row([
        dbc.Col(
            item,
            width='auto',
        )
        for item in layout
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
    Output('scatterplot-data', 'data'),
    Input('focused-player', 'data'),
    Input('current-split', 'data'),
    prevent_initial_call=True,
)
def update_scatterplot_data(player: Dict[str, Any], split: str) -> Dict[str, Any]:
    if player is None:
        return no_update

    xyz = appdata[split].cluster_xyz
    sizes = appdata[split].cluster_sizes
    uniqueness = 100 * appdata[split].cluster_uniqueness

    return {
        'cluster_x': list(xyz['x']),
        'cluster_y': list(xyz['y']),
        'cluster_z': list(xyz['z']),
        'cluster_nplayers': list(sizes),
        'cluster_uniqueness': list(uniqueness)
    }


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
    Output('cluster-table-data:title', 'data'),
    Output('cluster-table-data:stats', 'data'),
    Input('current-clusterid', 'data'),
    State('current-split', 'data'),
    prevent_initial_call=True,
)
def update_cluster_table_data(clusterid, split) -> Tuple[int, Dict[str, int]]:
    if clusterid is None:
        skills = appdata[split].skills
        skills.append('total')
        return None, {s: None for s in skills}

    centroid = appdata[split].cluster_centroids.loc[clusterid]
    skills = centroid.index
    lvls = [np.round(i) for i in centroid]
    stats = {skill: lvl for skill, lvl in zip(skills, lvls)}

    total_lvl = appdata[split].cluster_quartiles.sel(
        skill='total',
        clusterid=clusterid,
        percentile=50
    ).item()
    total_lvl = np.round(total_lvl)
    stats['total'] = total_lvl

    return clusterid, stats


@app.callback(
    Output('player-table-data:title', 'data'),
    Output('player-table-data:stats', 'data'),
    Input('focused-player', 'data'),
    prevent_initial_call=True,
)
def update_player_table_data(player) -> Tuple[str, Dict[str, int]]:
    skills = osrs_skills(include_total=True)
    if player is None:
        return None, {s: None for s in skills}

    stats = {}
    for skill in skills:
        stat = player['stats'][skill]
        if stat == 0:
            stat = None
        stats[skill] = stat

    return player['username'], stats
