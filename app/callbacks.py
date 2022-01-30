import math

from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import get_level_tick_marks, validate_username, skill_format
from app.figures import get_scatterplot, get_boxplot


def add_callbacks(app, app_data, player_collection):
    all_skills = app_data['all']['skills']

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
        Input('username-text', 'value'),
        Input('current-split', 'value')
    )
    def query_player(username, split):
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
                return None
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

        quartiles = {}
        for i, q in enumerate(['min', 'q1', 'med', 'q3', 'max']):
            quartile = app_data[split]['cluster_quartiles'][cluster_id - 1, i, :]
            quartiles[q] = [None if math.isnan(v) else round(v) for v in quartile]

        return {
            'id': cluster_id,
            'size': app_data[split]['cluster_sizes'][cluster_id - 1],
            'quartiles': quartiles
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
        cluster_centroid = cluster['quartiles']['med']

        table_values = ['' if v is None else str(v) for v in cluster_centroid]
        if split == 'cb':
            table_values += 16 * ['']
        elif split == 'noncb':
            table_values = table_values[:1] + 7 * [''] + table_values[1:]

        return f"Cluster {cluster_id}", *table_values

    return app
