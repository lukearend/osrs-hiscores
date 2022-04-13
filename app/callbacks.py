from typing import List, Dict, Any, Tuple

import numpy as np
from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from plotly import graph_objects as go
from pymongo.database import Database

from app import skill_upper, load_app_data, format_skill, validate_username, get_level_tick_marks, CLUSTERIDS_COLL, \
    STATS_COLL, load_table_layout
from app.plotdata import compute_boxplot_data, compute_scatterplot_data
from app.figures import get_scatterplot, get_empty_boxplot
from src.analysis import osrs_skills


def add_callbacks(app: Dash, player_db: Database) -> Dash:


    @app.callback(
        Output('scatter-plot', 'figure'),
        Input('kmeans-k', 'value'),
        Input('n-neighbors', 'value'),
        Input('min-dist', 'value'),
        Input('current-split', 'value'),
        Input('current-skill', 'value'),
        Input('current-player', 'data'),
        Input('level-range', 'value'),
        Input('point-size', 'value')
    )
    def redraw_scatterplot(kmeans_k: int, n_neighbors: int, min_dist: float,
                           current_split: str, current_skill: str,
                           current_player: Dict[str, Any],
                           level_range: List[int], point_size: str):

        data = load_app_data(kmeans_k, n_neighbors, min_dist)
        df = compute_scatterplot_data(data[current_split], current_skill, level_range)

        color_label = f"{skill_upper(current_skill)}\nlevel"

        color_range = [500, 2277] if current_skill == 'total' else [1, 99]

        point_size = {'small': 1, 'medium': 2, 'large': 3}[point_size]

        axis_limits = data[current_split].xyz_axlims
        if current_player is None:
            highlight_xyz = None
        else:
            highlight_cluster = current_player['clusterids'][current_split]
            highlight_xyz = data.splits[current_split].cluster_xyz[highlight_cluster].to_numpy()

        return get_scatterplot(
            df,
            colorlims=color_range,
            colorlabel=color_label,
            pointsize=point_size,
            axlims=axis_limits,
            crosshairs=highlight_xyz
        )


    @app.callback(
        Output('current-skill', 'options'),
        Output('current-skill', 'value'),
        Input('current-split', 'value'),
        State('current-skill', 'value'),
        State('kmeans-k', 'value'),
        State('n-neighbors', 'value'),
        State('min-dist', 'value')
    )
    def set_split(current_split: str, current_skill: str,
                  kmeans_k: int, n_neighbors: int, min_dist: float):

        if not current_split:
            raise PreventUpdate

        data = load_app_data(kmeans_k, n_neighbors, min_dist)
        skills_in_split = ['total'] + data[current_split].skills
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
    def set_skill(new_skill, current_range):

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
        State('kmeans-k', 'value')
    )
    def query_player(username, kmeans_k):

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

        stats = player_db[STATS_COLL].find_one({'_id': username.lower()})
        clusterids = player_db[f'{CLUSTERIDS_COLL}-{kmeans_k}'].find_one({'_id': username.lower()})
        if not stats or not clusterids:
            return {
                'username': username,
                'response': 404  # not found
            }
        return {
            'username': username,
            'response': {
                'username': stats['username'],
                'clusterids': clusterids['clusterids'],
                'stats': stats['stats']
            }
        }


    @app.callback(
        Output('player-query-text', 'children'),
        Input('query-event', 'data'),
        Input('current-split', 'value'),
        State('kmeans-k', 'value'),
        State('n-neighbors', 'value'),
        State('min-dist', 'value')
    )
    def set_query_text(query: Dict[str, Any], current_split: str,
                       kmeans_k: int, n_neighbors: int, min_dist: float):

        username = query['username']
        response = query['response']
        if response is None:
            return ''
        elif response == 400:
            return f"'{username}' is not a valid username"
        elif response == 404:
            return f"no player '{username}' in dataset"

        data = load_app_data(kmeans_k, n_neighbors, min_dist)
        cluster_id = response['clusterids'][current_split]
        cluster_size = data[current_split].cluster_sizes[cluster_id - 1]
        uniqueness = data[current_split].cluster_uniqueness[cluster_id - 1]

        return f"Cluster {cluster_id} ({cluster_size} players, {uniqueness:.2%} unique)"


    @app.callback(
        Output('current-player', 'data'),
        Input('query-event', 'data')
    )
    def set_current_player(query: Dict[str, Any]):

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
        Output('current-cluster', 'data'),
        Input('current-player', 'data'),
        Input('current-split', 'value'),
        Input('scatter-plot', 'hoverData'),
        State('kmeans-k', 'value'),
        State('n-neighbors', 'value'),
        State('min-dist', 'value')
    )
    def set_current_cluster(player_data: Dict[str, Any], current_split: str, hover_data: Dict[str, Any],
                            kmeans_k: int, n_neighbors: int, min_dist: float) -> Dict[str, any]:

        if hover_data is None:
            if player_data is None:
                return None
            cluster_id = player_data['clusterid'][current_split]
        else:
            point = hover_data['points'][0]
            if point['curveNumber'] == 1:  # hovered over a line
                raise PreventUpdate
            cluster_id = point['customdata'][0]

        data = load_app_data(kmeans_k, n_neighbors, min_dist)
        cluster_size = data[current_split].cluster_sizes[cluster_id]
        uniqueness = data[current_split].cluster_uniqueness[cluster_id]
        medians = data[current_split].cluster_quartiles.loc[50, cluster_id, :]  # 50th percentile
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
    def update_player_table(player_data: Dict[str, Any]) -> Tuple[str]:

        if player_data is None:  # e.g. search box cleared
            return tuple(["Player stats"] + len(osrs_skills(include_total=True)) * [''])

        table_vals = [str(v) for v in player_data['stats']]
        return tuple([f"Player '{player_data['username']}'", *table_vals])


    @app.callback(
        Output('cluster-table-title', 'children'),
        *[Output(f'cluster-table-{s}', 'children') for s in osrs_skills(include_total=True)],
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
        State('kmeans-k', 'value'),
        State('n-neighbors', 'value'),
        State('min-dist', 'value')
    )
    def update_cluster_table(cluster_data: Dict[str, Any], current_split: str,
                             kmeans_k: int, n_neighbors: int, min_dist: float) -> Tuple[str]:

        if cluster_data is None:
            return ("Cluster stats", *['' for _ in osrs_skills(include_total=True)])

        table_skills = [skill for skill_row in load_table_layout() for skill in skill_row]
        table_vals = np.array(len(table_skills) * ['-'], dtype='object')
        total_col = table_skills.index('total')
        table_vals[total_col] = cluster_data['total_level']

        data = load_app_data(kmeans_k, n_neighbors, min_dist)
        for i, skill in enumerate(data[current_split].skills):
            skill_level = cluster_data['centroid'][i]
            table_i = table_skills.index(skill)
            table_vals[table_i] = skill_level

        return tuple([f"Cluster {cluster_data['id']}", *table_vals])


    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value')
    )
    def redraw_box_plot(current_split: str) -> go.Figure:
        return get_empty_boxplot(current_split)


    @app.callback(
        Output('box-plot', 'extendData'),
        Input('box-plot', 'figure'),
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
        State('kmeans-k', 'value'),
        State('n-neighbors', 'value'),
        State('min-dist', 'value')
    )
    def update_box_plot(_, current_cluster: Dict[str, Any], current_split: str,
                        kmeans_k: int, n_neighbors: int, min_dist: float) -> Dict[str, Any]:

        data = load_app_data(kmeans_k, n_neighbors, min_dist)[current_split]
        if current_cluster is None:
            plot_data = compute_boxplot_data(current_split, data, clusterid=None)
        else:
            plot_data = compute_boxplot_data(current_split, data, clusterid=current_cluster['id'])
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
        return f"Cluster {cluster['id']} level ranges "\
               f"({cluster['size']} {'player' if cluster['size'] == 1 else 'players'})"
