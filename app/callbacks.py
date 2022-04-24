""" Dynamic behavior of application. """

from datetime import datetime
from typing import List, Dict, Any, Tuple

import numpy as np
from dash import Dash, no_update, callback_context
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from plotly import graph_objects as go
from pymongo.collection import Collection

from app import load_table_layout, format_skill, skill_upper, validate_username, get_level_tick_marks
from app.plotdata import compute_boxplot_data, compute_scatterplot_data
from app.figures import get_scatterplot, get_empty_boxplot
from src.analysis import osrs_skills
from src.analysis.app import SplitData, mongo_get_player


def add_callbacks(app: Dash, app_data: Dict[str, SplitData], player_coll: Collection) -> Dash:

    @app.callback(
        Output('scatter-plot', 'figure'),
        Input('current-split', 'value'),
        Input('current-skill', 'value'),
        Input('current-player', 'data'),
        Input('clicked-cluster', 'data'),
        Input('level-range', 'value'),
        Input('point-size', 'value')
    )
    def redraw_scatterplot(current_split: str,
                           current_skill: str,
                           current_player: Dict[str, Any],
                           clicked_cluster: int,
                           level_range: List[int],
                           point_size: str) -> go.Figure:

        split_data = app_data[current_split]
        df = compute_scatterplot_data(split_data, current_skill, level_range)

        if current_player is None:
            player_xyz = None
        else:
            player_cluster = current_player['clusterid'][current_split]
            player_xyz = split_data.cluster_xyz.loc[player_cluster, :].to_numpy()

        if clicked_cluster is None:
            clicked_xyz = None
        else:
            clicked_xyz = split_data.cluster_xyz.loc[clicked_cluster, :].to_numpy()

        return get_scatterplot(
            df,
            colorbar_label=f"{skill_upper(current_skill)}\nlevel",
            colorbar_limits=[500, 2277] if current_skill == 'total' else [1, 99],
            axis_limits=split_data.xyz_axlims,
            size_factor={'small': 1, 'medium': 2, 'large': 3}[point_size],
            player_crosshairs=player_xyz,
            clicked_crosshairs=clicked_xyz
        )


    @app.callback(
        Output('current-skill', 'options'),
        Output('current-skill', 'value'),
        Input('current-split', 'value'),
        State('current-skill', 'value'),
    )
    def set_split(current_split: str, current_skill: str) -> Tuple[List[str], str]:

        if not current_split:
            raise PreventUpdate

        split_data = app_data[current_split]
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
    def set_skill(new_skill, current_range) -> Tuple[int, int, int, Dict[int, str]]:

        if not new_skill:
            raise PreventUpdate

        if current_range[0] > 98 or current_range[1] > 99 == [1, 2277] and new_skill != 'total':
            new_range = [1, 99]
        elif new_skill == 'total':
            new_range = [1, 2277]
        else:
            new_range = no_update

        marks = get_level_tick_marks(new_skill)

        if new_skill == 'total':
            return 1, 2277, new_range, marks

        return 1, 99, new_range, marks


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
    def set_query_text(query: Dict[str, Any], current_split: str) -> str:

        username = query['username']
        response = query['response']
        if response is None:
            return ''
        elif response == 400:
            return f"'{username}' is not a valid username"
        elif response == 404:
            return f"no player '{username}' in dataset"

        split_data = app_data[current_split]
        cluster_id = response['clusterids'][current_split]
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
        Output('last-clicked-ts', 'data'),
        Input('scatter-plot', 'clickData'),
        Input('current-split', 'value'),
        State('clicked-cluster', 'data'),
        State('last-clicked-ts', 'data')
    )
    def set_clicked_cluster(click_data: Dict[str, Any],
                            current_split: str,
                            current_cluster: int,
                            last_clicked_ts: float) -> Tuple[int, int]:

        trigger = callback_context.triggered[0]['prop_id']
        if trigger == 'current-split.value':
            return None, no_update

        elif trigger == 'scatter-plot.clickData':
            if click_data is None:
                raise PreventUpdate

            clicked_cluster = click_data['points'][0]['customdata'][0]

            now = datetime.now().timestamp()
            debounce = True if last_clicked_ts and now - last_clicked_ts < 0.3 else False
            if clicked_cluster == current_cluster or current_cluster is None and debounce:
                raise PreventUpdate

            if current_cluster == clicked_cluster:
                return None, now
            return clicked_cluster, now

        raise PreventUpdate


    @app.callback(
        Output('current-cluster', 'data'),
        Input('current-player', 'data'),
        Input('current-split', 'value'),
        Input('scatter-plot', 'hoverData'),
        State('clicked-cluster', 'data'),
    )
    def set_current_cluster(player_data: Dict[str, Any],
                            current_split: str,
                            hover_data: Dict[str, Any],
                            clicked_cluster: int) -> Dict[str, any]:

        if hover_data is not None:
            point = hover_data['points'][0]
            if point['curveNumber'] == 1:  # hovered over a line
                raise PreventUpdate
            cluster_id = point['customdata'][0]
        elif clicked_cluster is not None:
            cluster_id = clicked_cluster
        elif player_data is not None:
            cluster_id = player_data['clusterid'][current_split]
        else:
            return None

        split_data = app_data[current_split]
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
    def update_cluster_table(cluster_data: Dict[str, Any], current_split: str) -> Tuple[str, ...]:

        table_skills = load_table_layout(flat=True)
        if cluster_data is None:
            return tuple(["Cluster stats", *['' for _ in table_skills]])

        table_vals = np.array(len(table_skills) * [''], dtype='object')
        total_col = table_skills.index('total')
        table_vals[total_col] = cluster_data['total_level']

        split_data = app_data[current_split]
        for i, skill in enumerate(split_data.skills):
            skill_level = cluster_data['centroid'][i]
            table_i = table_skills.index(skill)
            table_vals[table_i] = skill_level if skill_level > 0 else '-'

        return tuple([f"Cluster {cluster_data['id']}", *table_vals])


    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value')
    )
    def redraw_box_plot(current_split: str) -> go.Figure:
        return get_empty_boxplot(current_split, app_data[current_split].skills)


    @app.callback(
        Output('box-plot', 'extendData'),
        Input('box-plot', 'figure'),
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
    )
    def update_box_plot(_, current_cluster: Dict[str, Any], current_split: str) -> Dict[str, Any]:

        split_data = app_data[current_split]
        if current_cluster is None:
            plot_data = compute_boxplot_data(split_data, clusterid=None)
        else:
            plot_data = compute_boxplot_data(split_data, clusterid=current_cluster['id'])
        return [
            {
                'lowerfence': [plot_data['lowerfence']],
                'q1': [plot_data['q1']],
                'median': [plot_data['median']],
                'q3': [plot_data['q3']],
                'upperfence': [plot_data['upperfence']]
            },
            [0], len(plot_data['median'])
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

    return app
