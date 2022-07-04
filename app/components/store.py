from typing import Any, List, Dict, Tuple

import dash_bootstrap_components as dbc
import numpy as np
from dash import Output, Input, dcc, State, callback_context, no_update

from app import app, appdata
from app.helpers import get_trigger
from src.common import osrs_skills


def store_vars(show=True):
    storevars = [
        dcc.Store('current-players', data=[]),   # List[Dict[str, Any]]
        dcc.Store('queried-player'),             # Dict[str, Any]
        dcc.Store('clicked-blob'),               # str
        dcc.Store('closed-blob'),                # str
        dcc.Store('focused-player'),             # str
        dcc.Store('current-clusterid'),          # int
        dcc.Store('current-split', data='all'),  # str
        dcc.Store('point-size', data='small'),   # str
        dcc.Store('cluster-table-data:title'),   # int
        dcc.Store('player-table-data:title'),    # str
        dcc.Store('cluster-table-data:stats'),   # Dict[str, int]
        dcc.Store('player-table-data:stats'),    # Dict[str, int]
        dcc.Store('scatterplot-data'),           # Dict[str, Any]
        dcc.Store('boxplot-data'),               # Dict[str, Any]
    ]

    vars = dbc.Col([var for var in storevars])
    if not show:
        return vars

    showvars = storevars
    if isinstance(show, list):  # `show` can be a list of indices of storevars to display
        showvars = [storevars[i] for i in show]

    display = []
    for var in showvars:
        containerid = f'{var.id}:container'
        container = dbc.Row(
            [
                dbc.Col(var.id + ': ', width='auto'),
                dbc.Col(id=containerid),
            ],
            className='g-2',
        )
        display.append(container)

        @app.callback(
            Output(containerid, 'children'),
            Input(var.id, 'data'),
        )
        def update_container(newval: Any) -> str:
            return str(newval)

    return dbc.Col([
        vars,
        dbc.Row([
            dbc.Col(
                item,
                width='auto',
            ) for item in display
        ])
    ])


def get_player(player_list, uname: str) -> Dict[str, Any]:
    for p in player_list:
        if p['username'] == uname:
            return p
    return None


def del_player(player_list, uname: str) -> List[Dict[str, Any]]:
    return [p for p in player_list if p['username'] != uname]


def add_player(player_list, player: Dict[str, Any]) -> List[Dict[str, Any]]:
    player_list = del_player(player_list, player['username'])
    player_list.append(player)
    return player_list


@app.callback(
    Output('current-players', 'data'),
    Input('closed-blob', 'data'),
    Input('queried-player', 'data'),
    State('current-players', 'data'),
    prevent_initial_call=True,
)
def update_player_list(closed_uname: str,
                       queried_player: Dict[str, Any],
                       player_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    triggerid, _ = get_trigger(callback_context)

    new_players = no_update
    if triggerid == 'closed-blob':
        new_players = del_player(player_list, closed_uname)
    elif triggerid == 'queried-player':
        new_players = add_player(player_list, queried_player)

    return new_players


@app.callback(
    Output('focused-player', 'data'),
    Input('clicked-blob', 'data'),
    Input('closed-blob', 'data'),
    Input('queried-player', 'data'),
    State('focused-player', 'data'),
    State('current-players', 'data'),
    prevent_initial_call=True,
)
def updated_focused_player(clicked_uname: str,
                           closed_uname: str,
                           queried_player: Dict[str, Any],
                           focused_player: str,
                           player_list: List[Dict[str, Any]]) -> Dict[str, Any]:

    triggerid, _ = get_trigger(callback_context)

    new_player = no_update
    if triggerid == 'clicked-blob':
        new_player = get_player(player_list, clicked_uname)
    elif triggerid == 'closed-blob':
        if closed_uname == focused_player:
            new_player = None
    elif triggerid == 'queried-player':
        new_player = queried_player['username']

    return new_player


@app.callback(
    Output('current-clusterid', 'data'),
    Input('focused-player', 'data'),
    Input('current-split', 'data'),
    State('current-players', 'data'),
    prevent_initial_call=True,
)
def update_current_cluster(uname: str,
                           split: str,
                           player_list: List[Dict[str, Any]]) -> int:

    player = get_player(player_list, uname)
    if not player:
        return no_update
    return player['clusterids'][split]


@app.callback(
    Output('scatterplot-data', 'data'),
    Input('current-split', 'data'),
    Input('current-players', 'data'),
    prevent_initial_call=True,
)
def update_scatterplot_data(split: str,
                            player_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if split is None:
        return no_update

    xyz = appdata[split].cluster_xyz
    sizes = appdata[split].cluster_sizes
    uniqueness = appdata[split].cluster_uniqueness * 100

    axlims = appdata[split].xyz_axlims
    xmin, xmax = axlims['x']
    ymin, ymax = axlims['y']
    zmin, zmax = axlims['z']

    usernames = []
    players_x = []
    players_y = []
    players_z = []
    for p in player_list:
        usernames.append(p['username'])
        cid = p['clusterids'][split]
        x, y, z = appdata[split].cluster_xyz.loc[cid]
        players_x.append(x)
        players_y.append(y)
        players_z.append(z)

    return {
        'cluster_x': list(xyz['x']),
        'cluster_y': list(xyz['y']),
        'cluster_z': list(xyz['z']),
        'cluster_nplayers': list(sizes),
        'cluster_uniqueness': list(uniqueness),
        'axis_limits': {
            'x': (xmin, xmax),
            'y': (ymin, ymax),
            'z': (zmin, zmax),
        },
        'usernames': usernames,
        'players_x': players_x,
        'players_y': players_y,
        'players_z': players_z,
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
    State('current-players', 'data'),
)
def update_player_table_data(uname: str,
                             current_players: List[Dict[str, Any]]) -> Tuple[str, Dict[str, int]]:
    skills = osrs_skills(include_total=True)
    if uname is None:
        return None, {s: None for s in skills}

    player = get_player(current_players, uname)
    if not player:
        return no_update, no_update

    stats = {}
    for skill in skills:
        stat = player['stats'][skill]
        if stat == 0:
            stat = None
        stats[skill] = stat

    return player['username'], stats
