from typing import List, Dict

from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from pymongo import MongoClient
import numpy as np

from app import (
    validate_username, format_skill, default_n_neighbors, default_min_dist,
    get_level_tick_marks, get_color_label, get_color_range, get_point_size
)
from app.data import get_boxplot_inds, compute_boxplot_data, compute_scatterplot_data
from app.figures import get_scatterplot, get_empty_boxplot
from src.results import AppData


def add_callbacks(app: Dash, appdata: AppData, appdb: MongoClient) -> Dash:
    all_skills = appdata.splitdata["all"].skills
    boxplot_inds_per_split = get_boxplot_inds(appdata)

    @app.callback(
        Output('scatter-plot', 'figure'),
        Input('current-split', 'value'),
        Input('current-skill', 'value'),
        Input('level-range', 'value'),
        Input('n-neighbors', 'value'),
        Input('min-dist', 'value'),
        Input('current-player', 'data'),
        Input('point-size', 'value')
    )
    def redraw_scatterplot(split: str, skill: str, level_range: List[int],
                           n_neighbors: int, min_dist: float, player_data: Dict, ptsize_name: str):
        df = compute_scatterplot_data(appdata.splitdata[split], skill, level_range, n_neighbors, min_dist)
        color_label = get_color_label(skill)
        color_range = get_color_range(skill)
        point_size = get_point_size(ptsize_name)

        axis_limits = appdata.splitdata[split].axlims[n_neighbors][min_dist]
        if player_data is None:
            highlight_xyz = None
        else:
            highlight_cluster = player_data['clusterid'][split]
            highlight_xyz = appdata.splitdata[split].clusterdata.xyz[n_neighbors][min_dist][highlight_cluster - 1]

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
        Output('n-neighbors', 'value'),
        Output('min-dist', 'value'),
        Input('current-split', 'value'),
        State('current-skill', 'value')
    )
    def set_split(split, current_skill):
        if not split:
            raise PreventUpdate

        excluded_skills = {
            'all': [],
            'cb': all_skills[8:],
            'noncb': all_skills[1:8]
        }[split]

        options = []
        for skill in all_skills:
            options.append({
                'label': format_skill(skill),
                'value': skill,
                'disabled': True if skill in excluded_skills else False
            })

        if current_skill in excluded_skills:
            new_skill = 'total'
        else:
            new_skill = current_skill

        n_neighbors = default_n_neighbors(split)
        min_dist = default_min_dist(split)

        return options, new_skill, n_neighbors, min_dist

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
        Input('username-text', 'value')
    )
    def query_player(username):
        if not username:
            return {
                'query': '',
                'response': None
            }

        if not validate_username(username):
            return {
                'query': username,
                'response': 400  # invalid
            }

        response = appdb["players"].find_one({'_id': username.lower()})
        if not response:
            return {
                'query': username,
                'response': 404  # not found
            }
        return {
            'query': username,
            'response': {
                'username': response['username'],
                'cluster_ids': response['cluster_ids'],
                'stats': response['stats']
            }
        }

    @app.callback(
        Output('player-query-text', 'children'),
        Input('query-event', 'data'),
        Input('current-split', 'value')
    )
    def set_query_text(query_event, split):
        query_username = query_event['query']
        response = query_event['response']

        if response is None:
            return ''
        elif response == 400:
            return f"'{query_username[:12]}' is not a valid username"
        elif response == 404:
            return f"no player '{query_username}' in dataset"

        cid = response['cluster_ids'][split]
        cluster_size = appdata.splitdata[split].clusterdata.sizes[cid - 1]
        uniqueness = appdata.splitdata[split].clusterdata.uniqueness[cid - 1]
        return f"Cluster {cid} ({cluster_size} players, {uniqueness:.2%} unique)"

    @app.callback(
        Output('current-player', 'data'),
        Input('query-event', 'data')
    )
    def set_current_player(query_event):
        response = query_event['response']
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
            'clusterid': response['cluster_ids'],
            'stats': stats
        }

    @app.callback(
        Output('current-cluster', 'data'),
        Input('current-player', 'data'),
        Input('current-split', 'value'),
        Input('scatter-plot', 'hoverData')
    )
    def set_current_cluster(player_data, split, hover_data):
        if hover_data is None:
            if player_data is None:
                return None
            clusterid = player_data['clusterid'][split]
        else:
            pt = hover_data['points'][0]
            if pt['curveNumber'] == 1:  # hovered over a line
                raise PreventUpdate
            clusterid = pt['customdata'][0]

        cluster_size = appdata.splitdata[split].clusterdata.sizes[clusterid - 1]
        uniqueness = appdata.splitdata[split].clusterdata.uniqueness[clusterid - 1]
        centroid = appdata.splitdata[split].clusterdata.centroids[clusterid - 1]
        return {
            'id': clusterid,
            'size': cluster_size,
            'uniqueness': uniqueness,
            'centroid': [None if np.isnan(v) else round(v) for v in centroid]
        }

    @app.callback(
        Output('player-table-title', 'children'),
        *(Output(f'player-table-{skill}', 'children') for skill in ["total"] + all_skills),
        Input('current-player', 'data')
    )
    def update_player_table(player_data):
        if player_data is None:  # e.g. search box cleared
            return "Player stats", *('' for _ in range(24))

        tablevals = [str(v) for v in player_data['stats']]
        return f"Player '{player_data['username']}'", *tablevals

    @app.callback(
        Output('cluster-table-title', 'children'),
        *(Output(f'cluster-table-{skill}', 'children') for skill in all_skills),
        Input('current-cluster', 'data'),
        State('current-split', 'value')
    )
    def update_cluster_table(cluster, split):
        if cluster is None:
            return "Cluster stats", *('' for _ in all_skills)

        split_skills = appdata.splitdata[split].skills
        start_ind = all_skills.index(split_skills[0])  # find start and end of skills
        end_ind = start_ind + len(split_skills)        # in centroid for this split

        tablevals = np.zeros(len(all_skills), dtype='object')
        for i, v in zip(range(start_ind, end_ind), cluster['centroid']):
            tablevals[i] = '-' if v is None else str(round(v))
        tablevals[:start_ind] = '-'
        tablevals[end_ind:] = '-'

        return f"Cluster {cluster['id']}", *tablevals

    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value')
    )
    def redraw_box_plot(split):
        return get_empty_boxplot(split)

    @app.callback(
        Output('box-plot', 'extendData'),
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
        Input('box-plot', 'figure')
    )
    def update_box_plot(cluster, split, _):
        split_data = appdata.splitdata[split]
        boxplot_inds = boxplot_inds_per_split[split]
        if cluster is None:
            plot_data = compute_boxplot_data(split_data, boxplot_inds, clusterid=None)
        else:
            plot_data = compute_boxplot_data(split_data, boxplot_inds, clusterid=cluster['id'])
        return [
            {
                'lowerfence': [plot_data['lowerfence']],
                'q1': [plot_data['q1']],
                'median': [plot_data['median']],
                'q3': [plot_data['q3']],
                'upperfence': [plot_data['upperfence']]
            },
            [0],
            len(plot_data['median'])
        ]

    @app.callback(
        Output('box-plot-text', 'children'),
        Input('current-cluster', 'data')
    )
    def update_box_plot_text(cluster):
        if cluster is None:
            return "Cluster level ranges"
        return f"Cluster {cluster['id']} level ranges "\
               f"({cluster['size']} {'player' if cluster['size'] == 1 else 'players'})"

    return app
