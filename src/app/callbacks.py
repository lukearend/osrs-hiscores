from typing import List, Dict

from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from pymongo.database import Collection
import numpy as np

from src import osrs_skills
from src.app.data import compute_boxplot_data, compute_scatterplot_data
from src.app.figures import get_scatterplot, get_empty_boxplot
from src.app import validate_username, format_skill, default_n_neighbors, default_min_dist, \
    get_level_tick_marks, get_color_label, get_color_range, get_point_size, AppData


def add_callbacks(app: Dash, app_data: AppData, player_coll: Collection) -> Dash:
    all_stats = osrs_skills(include_total=True)  # includes total level as first element

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
        df = compute_scatterplot_data(app_data.splitdata[split], skill, level_range, n_neighbors, min_dist)
        color_label = get_color_label(skill)
        color_range = get_color_range(skill)
        point_size = get_point_size(ptsize_name)

        axis_limits = app_data.splitdata[split].axlims[n_neighbors][min_dist]
        if player_data is None:
            highlight_xyz = None
        else:
            highlight_cluster = player_data['clusterid'][split]
            highlight_xyz = app_data.splitdata[split].clusterdata.xyz[n_neighbors][min_dist][highlight_cluster]

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

        split_skills = app_data.splitdata[split].skills
        split_stats = ['total'] + [s for s in all_stats if s in split_skills]

        options = []
        for skill in all_stats:
            options.append({
                'label': format_skill(skill),
                'value': skill,
                'disabled': False if skill in split_stats else True
            })

        new_skill = 'total' if current_skill not in split_stats else current_skill
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

        response = player_coll.find_one({'_id': username.lower()})
        if not response:
            return {
                'query': username,
                'response': 404  # not found
            }
        return {
            'query': username,
            'response': {
                'username': response['username'],
                'clusterids': response['clusterids'],
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
            return f"'{query_username}' is not a valid username"
        elif response == 404:
            return f"no player '{query_username}' in dataset"

        cid = response['clusterids'][split]
        cluster_size = app_data.splitdata[split].clusterdata.sizes[cid - 1]
        uniqueness = app_data.splitdata[split].clusterdata.uniqueness[cid - 1]
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
            'clusterid': response['clusterids'],
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

        cluster_size = app_data.splitdata[split].clusterdata.sizes[clusterid]
        uniqueness = app_data.splitdata[split].clusterdata.uniqueness[clusterid]
        centroid = app_data.splitdata[split].clusterdata.quartiles[clusterid, 2, :]  # median
        return {
            'id': clusterid,
            'size': cluster_size,
            'uniqueness': uniqueness,
            'centroid': [None if np.isnan(v) else round(v) for v in centroid]
        }

    @app.callback(
        Output('player-table-title', 'children'),
        *(Output(f'player-table-{s}', 'children') for s in all_stats),
        Input('current-player', 'data')
    )
    def update_player_table(player_data):
        if player_data is None:  # e.g. search box cleared
            return ("Player stats", *('' for _ in range(len(all_stats))))

        tablevals = [str(v) for v in player_data['stats']]
        return (f"Player '{player_data['username']}'", *tablevals)

    @app.callback(
        Output('cluster-table-title', 'children'),
        *(Output(f'cluster-table-{s}', 'children') for s in all_stats),
        Input('current-cluster', 'data'),
        State('current-split', 'value')
    )
    def update_cluster_table(cluster, split):
        if cluster is None:
            return ("Cluster stats", *('' for _ in all_stats))

        tablevals = np.zeros(len(all_stats), dtype='object')
        total_level, *skill_levels = cluster['centroid']

        split_skills = app_data.splitdata[split].skills
        i_start = all_stats.index(split_skills[0])  # find start and end index of skills in
        i_end = i_start + len(split_skills)         # split within list of all stat names

        tablevals[0] = total_level
        for i, v in zip(range(i_start, i_end), skill_levels):
            tablevals[i] = '-' if v is None else str(round(v))
        tablevals[1:i_start] = '-'
        tablevals[i_end:] = '-'

        return (f"Cluster {cluster['id']}", *tablevals)

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
        split_data = app_data.splitdata[split]
        if cluster is None:
            plot_data = compute_boxplot_data(split, split_data, clusterid=None)
        else:
            plot_data = compute_boxplot_data(split, split_data, clusterid=cluster['id'])
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
