import json
import pathlib

import numpy as np
from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import get_level_tick_marks, validate_username, skill_format
from app.figures import get_scatterplot, get_boxplot


def add_callbacks(app, app_data, player_collection):
    all_skills = app_data['all']['skills']

    # Build utility functions for reordering skills from canonical order
    # to order of tick marks along x-axis of box plot.
    boxplot_file = pathlib.Path(__name__).resolve().parent / 'assets' / 'boxplot_ticks.json'
    with open(boxplot_file, 'r') as f:
        boxplot_skills = json.load(f)

    reorder_fn = {}
    for split in app_data.keys():
        split_skills = app_data[split]['skills'][1:]  # exclude total level
        reorder_inds = [split_skills.index(skill) for skill in boxplot_skills[split]]
        reorder_fn[split] = lambda arr, reorder_inds=reorder_inds: arr[reorder_inds]

    @app.callback(
        Output('scatter-plot', 'figure'),
        Input('current-split', 'value'),
        Input('current-skill', 'value'),
        Input('level-range', 'value'),
        Input('current-player', 'data'),
        Input('point-size', 'value'),
        Input('n-neighbors', 'value'),
        Input('min-dist', 'value')
    )
    def redraw_scatterplot(split, skill, level_range, player_data, point_size, n_neighbors, min_dist):
        if player_data is None:
            highlight_cluster = None
        else:
            highlight_cluster = player_data['cluster_ids'][split]
        return get_scatterplot(app_data[split], skill, level_range, point_size,
                               n_neighbors, min_dist, highlight_cluster=highlight_cluster)

    @app.callback(
        Output('current-skill', 'options'),
        Output('current-skill', 'value'),
        Output('n-neighbors', 'value'),
        Output('min-dist', 'value'),
        Input('current-split', 'value'),
        State('current-skill', 'value')
    )
    def choose_split(split, current_skill):
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
                'label': skill_format(skill),
                'value': skill,
                'disabled': True if skill in excluded_skills else False
            })

        if current_skill in excluded_skills:
            new_skill = 'total'
        else:
            new_skill = current_skill

        n_neighbors, min_dist = {
            'all': (5, 0.25),
            'cb': (15, 0.25),
            'noncb': (5, 0.00)
        }[split]

        return options, new_skill, n_neighbors, min_dist

    @app.callback(
        Output('level-range', 'min'),
        Output('level-range', 'max'),
        Output('level-range', 'value'),
        Output('level-range', 'marks'),
        Input('current-skill', 'value'),
        State('level-range', 'value')
    )
    def choose_skill(new_skill, current_range):
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

        response = player_collection.find_one({'_id': username.lower()})
        if not response:
            return {
                'query': username,
                'response': 404  # not found
            }

        # todo: read
        # todo: transform stats to dict with stat names
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

        cluster_id = response['cluster_ids'][split]
        cluster_size = app_data[split]['cluster_sizes'][cluster_id - 1]
        uniqueness = app_data[split]['cluster_uniqueness'][cluster_id - 1]
        return f"cluster {cluster_id} ({cluster_size} players, {uniqueness:.2%} unique)"

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
        return response

    @app.callback(
        Output('current-cluster', 'data'),
        Input('current-player', 'data'),
        Input('scatter-plot', 'hoverData'),
        Input('current-split', 'value'),
        State('scatter-plot', 'figure')
    )
    def set_current_cluster(player_data, hover_data, split, scatterplot):
        if hover_data is None:
            if player_data is None:
                num_skills = len(app_data[split]['skills'])
                return {
                    'id': None,
                    'size': None,
                    'centroid': np.full(num_skills, np.nan),
                    'boxplot': {
                        q: np.full(num_skills, np.nan)
                        for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']
                    }
                }
            else:
                cluster_id = player_data['cluster_ids'][split]
        else:
            pt = hover_data['points'][0]
            if pt['curveNumber'] == 1:  # hovered over a line
                raise PreventUpdate
            pt_idx = pt['pointNumber']

            if scatterplot is None:
                raise PreventUpdate
            trace_data = scatterplot['data'][0]
            point_data = trace_data['customdata'][pt_idx]
            cluster_id = point_data[0]

        size = app_data[split]['cluster_sizes'][cluster_id - 1]
        uniqueness = app_data[split]['cluster_uniqueness'][cluster_id - 1]

        quartiles = app_data[split]['cluster_quartiles'][cluster_id - 1]
        quartiles = quartiles[:, 1:]  # drop total level
        q0, q1, q2, q3, q4 = quartiles
        iqr = q3 - q1
        lower_fence = np.maximum(q1 - 1.5 * iqr, q0)
        upper_fence = np.minimum(q3 - 1.5 * iqr, q4)

        centroid = np.round(q2)

        reorder = reorder_fn[split]
        boxplot = {
            'lowerfence': reorder(np.round(lower_fence)),
            'q1': reorder(np.round(q1)),
            'median': reorder(np.round(q2)),
            'q3': reorder(np.round(q3)),
            'upperfence': reorder(np.round(upper_fence))
        }

        return {
            'id': cluster_id,
            'size': size,
            'uniqueness': uniqueness,
            'centroid': centroid,
            'boxplot': boxplot
        }

    @app.callback(
        Output('player-table-title', 'children'),
        *(Output(f'player-table-{skill}', 'children') for skill in all_skills),
        Input('current-player', 'data')
    )
    def update_player_table(player_data):
        if player_data is None:  # e.g. search box cleared
            return "Player stats", *('' for _ in range(24))

        table_values = [str(v) for v in player_data['stats']]
        return f"Player '{player_data['username']}'", *table_values

    @app.callback(
        Output('cluster-table-title', 'children'),
        *(Output(f'cluster-table-{skill}', 'children') for skill in all_skills),
        Input('current-cluster', 'data'),
        State('current-split', 'value')
    )
    def update_cluster_table(cluster, split):
        if cluster['id'] is None:
            return "Cluster stats", *('' for _ in range(24))

        cluster_id = cluster['id']
        cluster_centroid = cluster['centroid']

        table_values = ['-' if v is None else str(v) for v in cluster_centroid]
        if split == 'cb':
            table_values += 16 * ['']
        elif split == 'noncb':
            table_values = 7 * [''] + table_values
        table_values = [''] + table_values  # empty field for total level

        return f"Cluster {cluster_id}", *table_values

    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value')
    )
    def redraw_box_plot(split):
        return get_boxplot(split)

    # Use a client-side callback in JavaScript to update boxplot as fast as possible.
    app.clientside_callback(
        """
        function (cluster, split) {
            var numSkills;
            if (split == "all") {
                numSkills = 23
            } else if (split == "cb") {
                numSkills = 7
            } else if (split == "noncb") {
                numSkills = 16
            };
            return [[
                {
                    lowerfence: [cluster.boxplot.lowerfence],
                    q1: [cluster.boxplot.q1],
                    median: [cluster.boxplot.median],
                    q3: [cluster.boxplot.q3],
                    upperfence: [cluster.boxplot.upperfence],
                },
                [0],
                numSkills
            ]]
        }
        """,
        [Output('box-plot', 'extendData')],
        [Input('current-cluster', 'data')],
        [State('current-split', 'value')]
    )

    @app.callback(
        Output('box-plot-text', 'children'),
        Input('current-cluster', 'data')
    )
    def update_box_plot_text(cluster):
        if cluster['id'] is None:
            return "Cluster level ranges"
        return f"Cluster {cluster['id']} level ranges "\
               f"({cluster['size']} player{'' if cluster['size'] == 1 else 's'})"

    return app
