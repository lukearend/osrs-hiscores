import string

import numpy as np
import dash_html_components as html
from dash import callback_context, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import get_level_tick_marks, validate_username, skill_pretty
from app.figures import get_scatterplot, get_boxplot


def add_callbacks(app, app_data, player_collection):

    @app.callback(
        Output('scatter-plot', 'figure'),
        Input('split-dropdown', 'value'),
        Input('skill-dropdown', 'value'),
        Input('level-selector', 'value'),
        Input('selected-user', 'children'),
        Input('point-size-dropdown', 'value'),
        Input('n-neighbors-dropdown', 'value'),
        Input('min-dist-dropdown', 'value')
    )
    def redraw_figure(split, skill, level_range, user_text, point_size, n_neighbors, min_dist):
        triggers = [trigger['prop_id'] for trigger in callback_context.triggered]

        no_player = user_text.startswith('no player')
        invalid_player = 'not a valid username' in user_text
        if 'selected-user.children' in triggers and (no_player or invalid_player):
            raise PreventUpdate

        if not user_text or no_player or invalid_player:
            highlight_cluster = None
        else:

            # Get cluster ID from info string, e.g.
            # "'snakeylime': cluster 244 (41.38% unique)" -> 244
            i = user_text.find('cluster')
            words = user_text[i:].split(' ')
            highlight_cluster = int(words[1])

        return get_scatterplot(app_data[split], skill, level_range, point_size,
                               n_neighbors, min_dist, highlight_cluster=highlight_cluster)

    @app.callback(
        Output('skill-dropdown', 'options'),
        Output('skill-dropdown', 'value'),
        Input('split-dropdown', 'value'),
        State('skill-dropdown', 'value')
    )
    def choose_split(split, current_skill):
        if not split:
            print('x')
            raise PreventUpdate

        disabled = {
            'all': [],
            'cb': app_data['all']['skills'][8:],
            'noncb': app_data['all']['skills'][1:8]
        }[split]

        options = []
        for skill in app_data['all']['skills']:
            options.append({
                'label': skill_pretty(skill),
                'value': skill,
                'disabled': True if skill in disabled else False
            })

        if current_skill in disabled:
            new_skill = 'total'
        else:
            new_skill = current_skill

        return options, new_skill

    @app.callback(
        Output('level-selector', 'min'),
        Output('level-selector', 'max'),
        Output('level-selector', 'value'),
        Output('level-selector', 'marks'),
        Input('skill-dropdown', 'value'),
        State('level-selector', 'value')
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
        Output('selected-user', 'children'),
        Input('username-input', 'value'),
        Input('split-dropdown', 'value')
    )
    def lookup_player(username, split):
        if username:
            if not validate_username(username):
                return "'{}' is not a valid username".format(username[:12])

            player = player_collection.find_one({'_id': username.lower()})
            if player:
                username = player['username']
                cluster_id = player['cluster_id'][split]
                uniqueness = app_data[split]['cluster_uniqueness'][cluster_id]
                return "'{}': cluster {} ({:.2%} unique)".format(username, cluster_id, uniqueness)
            else:
                return "no player '{}' in dataset".format(username)

        return ''

    @app.callback(
        Output('selected-cluster', 'children'),
        Input('scatter-plot', 'clickData')
    )
    def select_cluster(click_data):
        print(click_data)
        return 'cluster 7'

    return app
