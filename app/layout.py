import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from app import get_level_marks, skill_pretty
from app.figures import get_scatterplot, get_boxplot


def build_layout(app, app_data):
    app.layout = dbc.Container([

        # App layout is a series of dbc.Rows.
        # Individual content items are wrapped by dbc.Col.

        dbc.Row(
            dbc.Col(
                [
                    html.Br(),
                    html.H1(children=html.Strong('OSRS player clusters')),
                    html.Div(children='''
                        Each point represents a cluster of OSRS players with similar stats.
                        The closer two clusters are, the more similar the accounts are in
                        each of those two clusters. Some clusters contain only a single
                        (highly) unique player; others comprise thousands or tens of thousands
                        of similar accounts. The size of each point corresponds to the number
                        of players in that cluster. Axes have no meaningful interpretation.
                    '''),
                    html.Br(),
                ]
            )
        ),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(children="Cluster by:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='split-dropdown',
                                    options=[
                                        {'label': 'All skills', 'value': 'all'},
                                        {'label': 'Combat skills', 'value': 'cb'},
                                        {'label': 'Non-combat skills', 'value': 'noncb'},
                                    ],
                                    value='all',
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=6
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(children="Color by:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='skill-dropdown',
                                    options=[
                                        {'label': skill_pretty(skill), 'value': skill}
                                        for skill in app_data['all']['skills']
                                    ],
                                    value='total',
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=6
                )
            ],
            align='center',
            style={'padding-bottom': '1vh'}
        ),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(children="n_neighbors:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='n-neighbors-dropdown',
                                    options=[
                                        {'label': str(n), 'value': n}
                                        for n in [5, 10, 15, 20]
                                    ],
                                    value=5,
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=6
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(children="min_dist:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='min-dist-dropdown',
                                    options=[
                                        {'label': '{:.2f}'.format(d), 'value': d}
                                        for d in [0.0, 0.1, 0.25, 0.50]
                                    ],
                                    value=0.0,
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=6
                )
            ],
            align='center',
            style={'padding-bottom': '1vh'}
        ),

        dbc.Row(
            [
                dbc.Col(
                    html.Div(children="Show levels:"),
                    width='auto'
                ),
                dbc.Col(
                    dcc.RangeSlider(
                        id='level-selector',
                        min=1,
                        max=2277,
                        step=1,
                        value=[1, 2277],
                        tooltip={'placement': 'bottom'},
                        allowCross=False,
                        marks=get_level_marks('total')
                    )
                )
            ],
            align='center',
            style={'padding-bottom': '1vh'}
        ),

        dbc.Row(
            [
                dbc.Col(
                    html.Div(children="Lookup player:"),
                    width='auto'
                ),
                dbc.Col(
                    dcc.Input(
                        id='username-input',
                        type='text',
                        placeholder="e.g. 'snakeylime'"
                    ),
                    width='auto'
                ),
                dbc.Col(
                    html.Div(id='selected-user')
                ),
            ],
            align='center',
            style={'padding-bottom': '1vh'}
        ),

        dbc.Row(
            dbc.Col(
                [
                    dcc.Graph(
                        id='scatter-plot',
                        figure=get_scatterplot(app_data['all'], 'total', [1, 2277], 5, 0.0),
                        style={'height': '80vh'},
                        clear_on_unhover=True
                    ),
                    dcc.Graph(
                        id='box-plot',
                        figure=get_boxplot(app_data['all']['cluster_quartiles'][244])
                    ),
                    html.Br()
                ]
            )
        ),
        dcc.Tooltip(id='tooltip'),
    ])

    return app
