from typing import Any, List, Dict, Tuple

import dash_bootstrap_components as dbc
from dash import Output, Input, dcc, State, callback_context, no_update

from app import app, appdata
from app.helpers import get_trigger


def store_vars():
    storevars = [
        dcc.Store('username-list', data=[]),
        dcc.Store('player-data-dict', data={}),
        dcc.Store('selected-username', data=None),
        dcc.Store('boxplot-cluster', data=None),
        dcc.Store('boxplot-data', data=None),
        dcc.Store('last-queried-player'),
        dcc.Store('last-closed-username'),
        dcc.Store('last-clicked-blob'),
    ]

    children = []
    for var in storevars:
        containerid = f'container:{var.id}'

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
            preview,
            width='auto',
        )
        for preview in children
    ])


@app.callback(
    Output('username-list', 'data'),
    Output('player-data-dict', 'data'),
    Input('last-queried-player', 'data'),
    Input('last-closed-username', 'data'),
    State('username-list', 'data'),
    State('player-data-dict', 'data'),
)
def update_username_list(queried_player: Dict[str, Any],
                         closed_player: str,
                         uname_list: List[str],
                         data_dict: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:

    triggerid, uname = get_trigger(callback_context)
    if triggerid is None:
        return no_update, no_update

    elif triggerid == 'last-queried-player':
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
    Output('selected-username', 'data'),
    Input('last-clicked-blob', 'data'),
    Input('last-queried-player', 'data'),
    Input('last-closed-username', 'data'),
    State('selected-username', 'data'),
)
def update_selected_username(clicked_blob: str,
                             player_query: Dict[str, Any],
                             closed_player: str,
                             current_uname: str) -> str:

    triggerid, uname = get_trigger(callback_context)
    if triggerid is None:
        return no_update

    elif triggerid == 'last-clicked-blob':
        current_uname = clicked_blob

    elif triggerid == 'last-queried-player':
        current_uname = player_query['username']

    elif triggerid == 'last-closed-username':
        if closed_player == current_uname:
            current_uname = None

    return current_uname


@app.callback(
    Output('boxplot-cluster', 'data'),
    Input('selected-username', 'data'),
    Input('current-split', 'data'),
    State('player-data-dict', 'data'),
)
def update_boxplot_cluster(uname: str, split: str, data_dict: Dict[str, Any]) -> int:
    if uname is None:
        return no_update
    return data_dict[uname]['clusterids'][split]


@app.callback(
    Output('boxplot-data', 'data'),
    Input('boxplot-cluster', 'data'),
    Input('current-split', 'data'),
)
def update_boxplot_data(clusterid: int, split: str) -> Dict[str, Any]:
    if clusterid is None:
        return no_update

    nplayers = appdata[split].cluster_sizes[clusterid].item()
    data = appdata[split].cluster_quartiles.sel(clusterid=clusterid)
    data = data.drop_sel(skill='total')
    skills = [s.item() for s in data.coords['skill']]

    boxdata = []
    for p in [0, 25, 50, 75, 100]:
        skill_lvls = data.sel(percentile=p)
        skill_lvls = [i.item() for i in skill_lvls]
        skill_lvls = dict(zip(skills, skill_lvls))
        boxdata.append(skill_lvls)

    return {
        'id': clusterid,
        'num_players': nplayers,
        'quartiles': boxdata
    }
