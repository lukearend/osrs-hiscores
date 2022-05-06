""" Dynamic application behavior. """

from typing import List, Dict, Any, Tuple

import numpy as np
from dash import Dash, no_update, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from plotly import graph_objects as go
from pymongo.collection import Collection

from src import osrs_skills
from src.app.helpers import load_table_layout, format_skill, validate_username, \
    get_level_tick_marks, get_color_label, get_point_size
from src.app.plotdata import boxplot_data, scatterplot_data
from src.app.figures import get_scatterplot, get_empty_boxplot
from src.data.types import SplitResults
from src.data.db import mongo_get_player


def add_callbacks(app: Dash, app_data: Dict[str, SplitResults], player_coll: Collection):

    @app.callback(
        Output('scatter-plot', 'figure'),
        Input('current-split', 'value'),
        Input('current-skill', 'value'),
        Input('current-player', 'data'),
        Input('clicked-cluster', 'data'),
        Input('level-range', 'value'),
        Input('point-size', 'value')
    )
    def redraw_scatterplot(split: str,
                           color_skill: str,
                           highlight_player: Dict[str, Any],
                           highlight_cluster: int,
                           cbar_range: List[int],
                           point_size: str) -> go.Figure:

        split_data = app_data[split]
        df = scatterplot_data(split_data, color_skill, cbar_range)

        player_xyz = None
        if highlight_player is not None:
            player_cluster = highlight_player['clusterid'][split]
            player_xyz = split_data.cluster_xyz.loc[player_cluster, :].to_numpy()

        clicked_xyz = None
        if highlight_cluster is not None:
            clicked_xyz = split_data.cluster_xyz.loc[highlight_cluster, :].to_numpy()

        return get_scatterplot(
            df,
            colorbar_label=get_color_label(color_skill),
            colorbar_ticks=get_level_tick_marks(color_skill),
            axis_limits=split_data.xyz_axlims,
            size_factor=get_point_size(point_size),
            player_crosshairs=player_xyz,
            clicked_crosshairs=clicked_xyz
        )

    @app.callback(
        Output('current-skill', 'options'),
        Output('current-skill', 'value'),
        Input('current-split', 'value'),
        State('current-skill', 'value'),
    )
    def set_split(new_split: str, current_skill: str) -> Tuple[List[str], str]:
        if not new_split:
            raise PreventUpdate

        split_data = app_data[new_split]
        skills_in_split = ['total'] + split_data.skills
        options = []
        for skill in osrs_skills(include_total=True):
            options.append({
                'label': format_skill(skill),
                'value': skill,
                'disabled': False if skill in skills_in_split else True
            })
        new_skill = current_skill if current_skill in skills_in_split else 'total'
        return options, new_skill

    @app.callback(
        Output('level-range', 'min'),
        Output('level-range', 'max'),
        Output('level-range', 'value'),
        Output('level-range', 'marks'),
        Input('current-skill', 'value'),
        State('level-range', 'value')
    )
    def set_skill(new_skill, level_range) -> Tuple[int, int, int, Dict[int, str]]:
        if not new_skill:
            raise PreventUpdate

        ticks = get_level_tick_marks(new_skill)
        new_range = ticks[0], ticks[-1]

        if new_range[0] > level_range[-1] or new_range[-1] < level_range[0]:
            new_range = ticks[0], ticks[-1]
        else:
            new_range = no_update

        marks = {i: str(i) for i in get_level_tick_marks(new_skill)}
        return ticks[0], ticks[-1], new_range, marks

    @app.callback(
        Output('query-event', 'data'),
        Input('username-text', 'value'),
    )
    def query_player(username) -> Dict[str, Any]:
        if not username:
            return {
                'username': '',
                'response': None
            }
        if not validate_username(username):
            return {
                'username': username,
                'response': 400  # invalid
            }

        player = mongo_get_player(player_coll, username)
        if not player:
            return {
                'username': username,
                'response': 404  # not found
            }
        return {
            'username': username,
            'response': {
                'username': player.username,
                'clusterids': player.clusterids,
                'stats': player.stats
            }
        }

    @app.callback(
        Output('player-query-text', 'children'),
        Input('query-event', 'data'),
        Input('current-split', 'value'),
    )
    def set_query_text(query: Dict[str, Any], split: str) -> str:
        username = query['username']
        response = query['response']
        if response is None:
            return ''
        elif response == 400:
            return f"'{username}' is not a valid username"
        elif response == 404:
            return f"no player '{username}' in dataset"

        split_data = app_data[split]
        cluster_id = response['clusterids'][split]
        cluster_size = split_data.cluster_sizes[cluster_id]
        uniqueness = split_data.cluster_uniqueness[cluster_id]

        return f"Cluster {cluster_id} ({cluster_size} players, {uniqueness:.2%} unique)"

    @app.callback(
        Output('current-player', 'data'),
        Input('query-event', 'data')
    )
    def set_current_player(query: Dict[str, Any]) -> Dict[str, Any]:
        response = query['response']
        if response is None:
            return None
        elif response == 400:
            raise PreventUpdate
        elif response == 404:
            raise PreventUpdate
        elif not response:
            raise PreventUpdate

        stats = [None if n == -1 else n for n in response['stats']]
        return {
            'username': response['username'],
            'clusterid': response['clusterids'],
            'stats': stats
        }

    @app.callback(
        Output('clicked-cluster', 'data'),
        Input('current-split', 'value'),
        Input('click-listener', 'event'),
        Input('scatter-plot', 'clickData')
    )
    def set_clicked_cluster(current_split: str,
                            click_event: Any,
                            click_data: Dict[str, Any]) -> Tuple[int, int]:

        triggers = [d['prop_id'] for d in callback_context.triggered]
        if 'current-split.value' in triggers:
            return None
        elif 'scatter-plot.clickData' in triggers:
            if click_data is None:
                raise PreventUpdate
            return click_data['points'][0]['customdata'][0]
        else:
            return None  # clicked on figure background

    @app.callback(
        Output('current-cluster', 'data'),
        Input('current-split', 'value'),
        Input('current-player', 'data'),
        Input('clicked-cluster', 'data'),
        Input('scatter-plot', 'hoverData'),
    )
    def set_current_cluster(split: str,
                            current_player: Dict[str, Any],
                            clicked_cluster: int,
                            hover_data: Dict[str, Any]) -> Dict[str, any]:

        cluster_id = None
        if current_player:
            cluster_id = current_player['clusterid'][split]
        if clicked_cluster is not None:
            cluster_id = clicked_cluster
        if hover_data:
            point = hover_data['points'][0]
            if point['curveNumber'] == 0:  # hovered over a line
                cluster_id = point['customdata'][0]
        if cluster_id is None:
            return None

        split_data = app_data[split]
        cluster_size = split_data.cluster_sizes[cluster_id]
        uniqueness = split_data.cluster_uniqueness[cluster_id]
        medians = split_data.cluster_quartiles.loc[50, cluster_id, :]  # 50th percentile
        centroid = medians.where(medians.skill != 'total', drop=True)
        return {
            'id': cluster_id,
            'size': cluster_size,
            'uniqueness': uniqueness,
            'centroid': [None if np.isnan(v) else round(v.item()) for v in centroid],
            'total_level': medians.loc['total'].item()
        }

    @app.callback(
        Output('player-table-title', 'children'),
        *[Output(f'player-table-{s}', 'children') for s in osrs_skills(include_total=True)],
        Input('current-player', 'data')
    )
    def update_player_table(player_data: Dict[str, Any]) -> Tuple[str, ...]:

        if player_data is None:  # e.g. search box cleared
            return tuple(["Player stats"] + len(osrs_skills(include_total=True)) * [''])

        table_vals = [str(n) if n > 0 else '-' for n in player_data['stats']]
        return tuple([f"Player '{player_data['username']}'", *table_vals])

    @app.callback(
        Output('cluster-table-title', 'children'),
        *[Output(f'cluster-table-{s}', 'children') for s in load_table_layout(flat=True)],
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
    )
    def update_cluster_table(cluster_data: Dict[str, Any], split: str) -> Tuple[str, ...]:

        table_skills = load_table_layout(flat=True)
        if cluster_data is None:
            return tuple(["Cluster stats", *['' for _ in table_skills]])

        table_vals = np.array(len(table_skills) * [''], dtype='object')
        total_col = table_skills.index('total')
        table_vals[total_col] = int(cluster_data['total_level'])

        split_data = app_data[split]
        for i, skill in enumerate(split_data.skills):
            skill_level = cluster_data['centroid'][i]
            table_i = table_skills.index(skill)
            table_vals[table_i] = skill_level if skill_level > 0 else '-'

        return tuple([f"Cluster {cluster_data['id']}", *table_vals])

    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value')
    )
    def redraw_box_plot(split: str) -> go.Figure:
        return get_empty_boxplot(split, app_data[split].skills)

    @app.callback(
        Output('box-plot', 'extendData'),
        Input('box-plot', 'figure'),
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
    )
    def update_box_plot(_, cluster: Dict[str, Any], split: str) -> Dict[str, Any]:

        split_data = app_data[split]
        if cluster is None:
            plot_data = boxplot_data(split_data, clusterid=None)
        else:
            plot_data = boxplot_data(split_data, clusterid=cluster['id'])
        return [
            {
                'lowerfence': [plot_data['lowerfence']],
                'q1': [plot_data['q1']],
                'median': [plot_data['median']],
                'q3': [plot_data['q3']],
                'upperfence': [plot_data['upperfence']]
            },
            [0],                      # insert index
            len(plot_data['median'])  # max length
        ]

    @app.callback(
        Output('box-plot-text', 'children'),
        Input('current-cluster', 'data')
    )
    def update_box_plot_text(cluster: Dict[str, Any]) -> str:
        if cluster is None:
            return "Cluster level ranges"
        players = 'player' if cluster['size'] == 1 else 'players'
        return f"Cluster {cluster['id']} level ranges ({cluster['size']} {players})"
