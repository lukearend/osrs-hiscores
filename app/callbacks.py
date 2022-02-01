import json
import pathlib

import numpy as np
import pandas as pd
from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import get_level_tick_marks, validate_username
from app.figures import get_scatterplot, get_boxplot


def add_callbacks(app, app_data, player_collection):
    all_skills = app_data['all']['skills']

    # Build utility functions for reordering skills from canonical order
    # to order of tick marks along x-axis of box plot.
    boxplot_file = pathlib.Path(__name__).resolve().parent / 'assets' / 'boxplot_ticks.json'
    with open(boxplot_file, 'r') as f:
        boxplot_skills = json.load(f)

    boxplot_skill_inds = {}
    for split in app_data.keys():
        split_skills = app_data[split]['skills'][1:]  # exclude total level
        reorder_inds = [split_skills.index(skill) for skill in boxplot_skills[split]]
        boxplot_skill_inds[split] = reorder_inds

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
    def redraw_scatterplot(split, skill, level_range, player_data, ptsize_name, n_neighbors, min_dist):
        # When level selector is used, we display only those clusters whose
        # interquartile range in the chosen skill overlaps the selected range.
        skill_i = app_data[split]['skills'].index(skill)
        levels_q1 = app_data[split]['cluster_quartiles'][:, 1, skill_i]  # 25th percentile
        levels_q3 = app_data[split]['cluster_quartiles'][:, 3, skill_i]  # 75th percentile

        level_min, level_max = level_range
        show_inds = np.where(np.logical_and(
            levels_q3 >= level_min,
            levels_q1 <= level_max,
            ))[0]

        cluster_ids = show_inds + 1
        xyz_data = app_data[split]['xyz'][n_neighbors][min_dist][show_inds]
        num_players = app_data[split]['cluster_sizes'][show_inds]
        uniqueness = 100 * app_data[split]['cluster_uniqueness'][show_inds]
        median_level = app_data[split]['cluster_quartiles'][:, 2, skill_i][show_inds]

        df = pd.DataFrame({
            'x': xyz_data[:, 0],
            'y': xyz_data[:, 1],
            'z': xyz_data[:, 2],
            'id': cluster_ids,
            'size': num_players,
            'uniqueness': uniqueness,
            'level': median_level
        })

        skill_name = skill[0].upper() + skill[1:]
        color_label = f"{skill_name}\nlevel"
        if skill == 'total':
            color_range = [500, 2277]
        else:
            color_range = [1, 99]

        if player_data is None:
            highlight_xyz = None
        else:
            highlight_cluster = player_data['id'][split]
            highlight_xyz = app_data[split]['xyz'][n_neighbors][min_dist][highlight_cluster - 1]

        axis_limits = app_data[split]['axis_limits'][n_neighbors][min_dist]
        point_size = {'small': 1, 'medium': 2, 'large': 3}[ptsize_name]

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
            skill_name = skill[0].upper() + skill[1:]
            options.append({
                'label': f"{skill_name} level",
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
        return f"Cluster {cluster_id} ({cluster_size} players, {uniqueness:.2%} unique)"

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

        return {
            'username': response['username'],
            'id': response['cluster_ids'],
            'stats': response['stats']
        }

    @app.callback(
        Output('current-cluster', 'data'),
        Input('current-player', 'data'),
        Input('scatter-plot', 'hoverData'),
        Input('current-split', 'value'),
        State('scatter-plot', 'figure')
    )
    def set_current_cluster(player_data, hover_data, split, scatterplot):
        if scatterplot is None:  # todo: why is this statement necessary?
            raise PreventUpdate

        if hover_data is None:
            if player_data is None:
                return None
            cluster_id = player_data['id'][split]
        else:
            pt = hover_data['points'][0]
            if pt['curveNumber'] == 1:  # hovered over a line
                raise PreventUpdate

            pt_idx = pt['pointNumber']
            trace_data = scatterplot['data'][0]
            point_data = trace_data['customdata'][pt_idx]
            cluster_id = point_data[0]

        cluster_size = app_data[split]['cluster_sizes'][cluster_id - 1]
        uniqueness = app_data[split]['cluster_uniqueness'][cluster_id - 1]
        median_levels = app_data[split]['cluster_quartiles'][cluster_id - 1, 2]

        return {
            'id': cluster_id,
            'size': cluster_size,
            'uniqueness': uniqueness,
            'centroid': median_levels
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
        if cluster is None:
            return "Cluster stats", *('' for _ in range(24))

        cluster_id = cluster['id']
        centroid = cluster['centroid'][1:]  # drop total level
        centroid = [None if np.isnan(v) else round(v) for v in centroid]

        table_values = ['-' if v is None else str(v) for v in centroid]
        if split == 'cb':
            table_values += 16 * ['']
        elif split == 'noncb':
            table_values = 7 * [''] + table_values
        table_values = [''] + table_values  # empty field for total level

        return f"Cluster {cluster_id}", *table_values

    @app.callback(
        Output('boxplot-data', 'data'),
        Input('current-cluster', 'data'),
        State('current-split', 'value')
    )
    def set_boxplot_data(cluster, split):
        num_skills = {'all': 23, 'cb': 7, 'noncb': 16}[split]
        boxplot_data = {'numskills': num_skills}

        if cluster is None:
            for q in ['lowerfence', 'q1', 'median', 'q3', 'upperfence']:
                boxplot_data[q] = np.full(num_skills, np.nan)
            return boxplot_data

        quartiles = app_data[split]['cluster_quartiles'][cluster['id'] - 1]
        quartiles = quartiles[:, 1:]  # drop total level
        q0, q1, q2, q3, q4 = quartiles
        iqr = q3 - q1
        lower_fence = np.maximum(q1 - 1.5 * iqr, q0)
        upper_fence = np.minimum(q3 - 1.5 * iqr, q4)

        data = np.array([lower_fence, q1, q2, q3, upper_fence])
        data = np.round(data)
        data = data[:, boxplot_skill_inds[split]]

        for i, q in enumerate(['lowerfence', 'q1', 'median', 'q3', 'upperfence']):
            boxplot_data[q] = data[i]

        return boxplot_data

    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value'),
        State('boxplot-data', 'data')
    )
    def redraw_box_plot(split, boxplot_data):
        if boxplot_data is None:
            return get_boxplot(split, data=None)
        return get_boxplot(split, data=boxplot_data)

    # Use a client-side callback in JavaScript so boxplot updates as fast as possible.
    app.clientside_callback(
        """
        function (boxplotData, figure, split) {
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
                    lowerfence: [boxplotData.lowerfence],
                    q1: [boxplotData.q1],
                    median: [boxplotData.median],
                    q3: [boxplotData.q3],
                    upperfence: [boxplotData.upperfence],
                },
                [0],
                boxplotData.numskills
            ]]
        }
        """,
        [Output('box-plot', 'extendData')],
        [Input('boxplot-data', 'data')]
    )

    @app.callback(
        Output('box-plot-text', 'children'),
        Input('current-cluster', 'data')
    )
    def update_box_plot_text(cluster):
        if cluster is None:
            return "Cluster level ranges"
        return f"Cluster {cluster['id']} level ranges "\
               f"({cluster['size']} player{'' if cluster['size'] == 1 else 's'})"

    return app
