from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import validate_username, format_skill, default_n_neighbors, default_min_dist,\
                get_level_tick_marks, get_color_label, get_color_range, get_point_size
from app.data import app_data, compute_scatterplot_data, compute_boxplot_data

from app.figures import get_scatterplot, get_boxplot


def add_callbacks(app, player_collection):
    all_skills = app_data['all']['skills']

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
    def redraw_scatterplot(split, skill, level_range, n_neighbors, min_dist, player_data, ptsize_name):
        df = compute_scatterplot_data(split, skill, level_range, n_neighbors, min_dist)
        color_label = get_color_label(skill)
        color_range = get_color_range(skill)
        point_size = get_point_size(ptsize_name)

        axis_limits = app_data[split]['axis_limits'][n_neighbors][min_dist]
        if player_data is None:
            highlight_xyz = None
        else:
            highlight_cluster = player_data['clusterid'][split]
            highlight_xyz = app_data[split]['xyz'][n_neighbors][min_dist][highlight_cluster - 1]

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

        response = player_collection.find_one({'_id': username.lower()})
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
            cluster_id = player_data['clusterid'][split]
        else:
            pt = hover_data['points'][0]
            if pt['curveNumber'] == 1:  # hovered over a line
                raise PreventUpdate
            cluster_id = pt['customdata'][0]

        cluster_size = app_data[split]['cluster_sizes'][cluster_id - 1]
        uniqueness = app_data[split]['cluster_uniqueness'][cluster_id - 1]
        median_levels = app_data[split]['cluster_quartiles'][cluster_id - 1, 2]
        return {
            'id': cluster_id,
            'size': cluster_size,
            'uniqueness': uniqueness,
            'centroid': [None if n != n else round(n) for n in median_levels]
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
        *(Output(f'cluster-table-{skill}', 'children') for skill in all_skills[1:]),
        Input('current-cluster', 'data'),
        State('current-split', 'value')
    )
    def update_cluster_table(cluster, split):
        if cluster is None:
            return "Cluster stats", *('' for _ in all_skills[1:])

        centroid = cluster['centroid'][1:]  # drop total level
        centroid = [None if v is None else round(v) for v in centroid]

        table_values = ['-' if v is None else str(v) for v in centroid]
        if split == 'cb':
            table_values += len(app_data['noncb']['skills'][1:]) * ['']
        elif split == 'noncb':
            table_values = len(app_data['cb']['skills'][1:]) * [''] + table_values

        return f"Cluster {cluster['id']}", *table_values

    @app.callback(
        Output('box-plot', 'figure'),
        Input('current-split', 'value')
    )
    def redraw_box_plot(split):
        return get_boxplot(split)

    @app.callback(
        Output('box-plot', 'extendData'),
        Input('current-cluster', 'data'),
        State('current-split', 'value'),
        Input('box-plot', 'figure')
    )
    def update_box_plot(cluster, split, _):
        if cluster is None:
            plot_data = compute_boxplot_data(split, cluster_id=None)
        else:
            plot_data = compute_boxplot_data(split, cluster_id=cluster['id'])
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
