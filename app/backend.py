""" Hidden state variables and logic. """

from typing import Any, List, Dict, Tuple

import numpy as np
from dash import Output, Input, dcc, State, callback_context, no_update

from app import app, appdata, styles
from app.helpers import get_trigger
from src.common import osrs_skills


STORE_VARS = [
    dcc.Store('current-players', data=[]),     # List[Dict[str, Any]]
    dcc.Store('queried-player'),               # Dict[str, Any]
    dcc.Store('clicked-blob'),                 # str
    dcc.Store('closed-blob'),                  # str
    dcc.Store('focused-player'),               # str
    dcc.Store('current-clusterid'),            # int
    dcc.Store('current-split', data='all'),    # str
    dcc.Store('point-size', data='small'),     # str
    dcc.Store('color-by-skill', data='total'), # str (WIP)
    dcc.Store('cluster-table-data:title'),     # int
    dcc.Store('player-table-data:title'),      # str
    dcc.Store('cluster-table-data:stats'),     # Dict[str, int]
    dcc.Store('player-table-data:stats'),      # Dict[str, int]
    dcc.Store('scatterplot-data'),             # Dict[str, Any]
    dcc.Store('boxplot-data'),                 # Dict[str, Any]
    dcc.Store('hovered-cluster'),              # int
]


# The current-players list is a core data structure.
#
# It is populated by successful queries from the player stats database
# and holds the players currently being displayed by the application.
#
# [
#     {
#         'username': 'snakeylime',
#         'color': '#636EFA',
#         'stats': {
#             'total': 1691,
#             'attack': 60,
#             ...
#             'construction': 84
#         }
#         'clusterids': {
#             'all': 533,
#             'cb': 1064,
#             'noncb': 410,
#         }
#     },
#     ...,
# ]


def add_player(player_list, queried_player: Dict[str, Any]) -> List[Dict[str, Any]]:
    player_list = del_player(player_list, queried_player['username'])

    player_colors = [p['color'] for p in player_list]
    new_player = queried_player.copy()
    new_player['color'] = new_color(player_colors)
    player_list.append(new_player)

    return player_list


def get_player(player_list, uname: str) -> Dict[str, Any]:
    for p in player_list:
        if p['username'] == uname:
            return p
    return None


def del_player(player_list, uname: str) -> List[Dict[str, Any]]:
    return [p for p in player_list if p['username'] != uname]


def new_color(current_colors, color_seq=None) -> str:
    """ Return the next color used in the player sequence. """

    if color_seq is None:
        color_seq = styles.PLAYER_COLOR_SEQ

    color_counts = {c: 0 for c in color_seq}
    for c in current_colors:
        color_counts[c] += 1

    # Pick the color which is least represented on screen
    min_count = min(color_counts.values())
    new_colors = [color for color, n in color_counts.items() if n == min_count]
    for c in color_seq:
        if c in new_colors:
            return c


def store(show_inds: List[int] = None):
    if show_inds is None:
        return dbc.Col([v for v in STORE_VARS])

    show_ids = [v.id for i, v in STORE_VARS if i in show_inds]
    containers = []
    for var_id in show_ids:
        container_id = f'{var_id}:container'

        @app.callback(
            Output(container_id, 'children'),
            Input(var_id, 'data'),
        )
        def update_container(newval: Any) -> str:
            return str(newval)

        c = dbc.Row(
            [
                dbc.Col(var_id + ': ', width='auto'),
                dbc.Col(id=container_id),
            ],
            className='g-2',
        )
        containers.append(c)

    return dbc.Col([
        dbc.Col([v for v in STORE_VARS]),
        dbc.Row([
            dbc.Col(
                c,
                width='auto',
            ) for c in containers
        ])
    ])


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
    if triggerid == 'closed-blob':
        return del_player(player_list, closed_uname)
    elif triggerid == 'queried-player':
        return add_player(player_list, queried_player)
    return no_update


@app.callback(
    Output('focused-player', 'data'),
    Input('clicked-blob', 'data'),
    Input('closed-blob', 'data'),
    Input('queried-player', 'data'),
    State('focused-player', 'data'),
    prevent_initial_call=True,
)
def updated_focused_player(clicked_uname: str,
                           closed_uname: str,
                           queried_player: Dict[str, Any],
                           focused_player: str) -> str:

    triggerid, _ = get_trigger(callback_context)
    if triggerid == 'clicked-blob':
        return clicked_uname
    elif triggerid == 'closed-blob':
        return None if closed_uname == focused_player else no_update
    elif triggerid == 'queried-player':
        return queried_player['username']
    return no_update


@app.callback(
    Output('current-clusterid', 'data'),
    Input('focused-player', 'data'),
    Input('current-split', 'data'),
    Input('hovered-cluster', 'data'),
    State('current-players', 'data'),
    prevent_initial_call=True,
)
def update_current_cluster(uname: str,
                           split: str,
                           hovered_id: int,
                           player_list: List[Dict[str, Any]]) -> int:

    player_id = None
    player = get_player(player_list, uname)
    if player:
        player_id = player['clusterids'][split]

    triggerid, _ = get_trigger(callback_context)
    if triggerid in ['focused-player', 'current-split']:
        return player_id
    elif triggerid == 'hovered-cluster':
        return player_id if hovered_id is None else hovered_id
    return no_update


@app.callback(
    Output('scatterplot-data', 'data'),
    Input('current-players', 'data'),
    Input('current-split', 'data'),
    Input('color-by-skill', 'data'),
    Input('level-range-slider', 'drag_value'),
    prevent_initial_call=True,
)
def update_scatterplot_data(player_list: List[Dict[str, Any]],
                            split: str,
                            skill: str,
                            lvl_range: Tuple[int, int]) -> Dict[str, Any]:

    if lvl_range is None:
        return no_update

    splitdata = appdata[split]
    median_lvls = np.array(splitdata.cluster_quartiles.sel(skill=skill, percentile=50))
    median_lvls = np.round(median_lvls)
    cluster_xyz = np.array(splitdata.cluster_xyz)
    cluster_nplayers = splitdata.cluster_sizes
    cluster_uniqueness = 100 * splitdata.cluster_uniqueness

    show_min = lvl_range[0] if lvl_range[0] != 1 else 0
    show_max = lvl_range[1]
    gt = show_min <= median_lvls
    lt = median_lvls <= show_max
    show_inds = np.logical_and(gt, lt).nonzero()[0]

    axlims = splitdata.xyz_axlims
    xmin, xmax = axlims['x']
    ymin, ymax = axlims['y']
    zmin, zmax = axlims['z']

    player_usernames = []
    player_clusterids = []
    player_colors = []
    for p in player_list:
        player_usernames.append(p['username'])
        player_clusterids.append(p['clusterids'][split])
        player_colors.append(p['color'])

    return {
        'current_skill': skill,
        'show_inds': show_inds,
        'cluster_xyz': cluster_xyz,
        'cluster_nplayers': cluster_nplayers,
        'cluster_uniqueness': cluster_uniqueness,
        'cluster_medians': median_lvls,
        'axis_limits': {
            'x': (xmin, xmax),
            'y': (ymin, ymax),
            'z': (zmin, zmax),
        },
        'player_usernames': player_usernames,
        'player_clusterids': player_clusterids,
        'player_colors': player_colors,
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

    splitdata = appdata[split]
    nplayers = int(splitdata.cluster_sizes[clusterid])
    quartiles = splitdata.cluster_quartiles.sel(clusterid=clusterid)
    quartiles = quartiles.drop_sel(skill='total')
    skills = np.array(quartiles.coords['skill'])

    boxdata = []
    for p in [0, 25, 50, 75, 100]:
        lvls = np.array(quartiles.sel(percentile=p))
        d = dict(zip(skills, lvls))
        boxdata.append(d)

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
        skills = appdata[split].skills + ['total']
        return None, {s: None for s in skills}

    splitdata = appdata[split]
    centroid = splitdata.cluster_centroids.loc[clusterid]
    skills = centroid.index
    lvls = np.round(centroid)
    stats = dict(zip(skills, lvls))

    totlvl = int(np.round(
        splitdata.cluster_quartiles.sel(
            skill='total',
            clusterid=clusterid,
            percentile=50
        )
    ))
    stats['total'] = totlvl

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


@app.callback(
    Output('hovered-cluster', 'data'),
    Input('scatterplot', 'hoverData'),
)
def update_hovered_cluster(hoverdata):
    if not hoverdata:
        return None

    pt = hoverdata['points'][0]
    clusterid = pt['customdata'][0]
    return clusterid
