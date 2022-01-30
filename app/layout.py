import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from app import get_level_tick_marks, skill_format
from app.figures import get_scatterplot, get_level_table, get_boxplot


def build_layout(app, app_data):
    app.layout = dbc.Container([

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
                                    id='current-split',
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
                                    id='current-skill',
                                    options=[
                                        {'label': skill_format(skill), 'value': skill}
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
                                html.Div(children="Structure:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='n-neighbors',
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
                                html.Div(children="Diffusion:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='min-dist',
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
                        id='level-range',
                        min=1,
                        max=2277,
                        step=1,
                        value=[1, 2277],
                        tooltip={'placement': 'bottom'},
                        allowCross=False,
                        marks=get_level_tick_marks('total')
                    )
                )
            ],
            align='center',
            style={'padding-bottom': '1vh'}
        ),

        dcc.Store(id='query-event'),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(html.Div(children="Lookup player:"), width='auto'),
                            dbc.Col(
                                dcc.Input(
                                    id='username-text',
                                    type='text',
                                    placeholder="input username",
                                    maxLength=12
                                ),
                                width='auto'
                            ),
                            dbc.Col(html.Div(id='player-query-text'))
                        ],
                        align='center'
                    ),
                    width=9
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(html.Div(children="Point size:"), width='auto'),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='point-size',
                                    options=[
                                        {'label': s, 'value': s}
                                        for s in ['small', 'medium', 'large']
                                    ],
                                    value='small',
                                    clearable=False
                                )
                            )
                        ],
                        align='center',
                        justify='end'
                    ),
                    width=3
                )
            ],
            style={'padding-bottom': '1vh'}
        ),

        dcc.Store(id='current-player'),
        dcc.Store(id='current-cluster'),
        dbc.Row([
            dbc.Col(
                [
                    html.Br(),
                    dbc.Row(
                        [
                            dbc.Col([
                                html.Strong(id='player-table-title'),
                                get_level_table(name='player-table'),
                            ]),
                            dbc.Col([
                                html.Strong(id='cluster-table-title'),
                                get_level_table(name='cluster-table')
                            ]),
                        ],
                        align='center'
                    ),

                    html.Br(),
                    dbc.Row(
                        dbc.Col(
                            dcc.Graph(
                                id='box-plot',
                                style={'height': '20vh'},
                            )
                        ),
                        align='center'
                    )
                ],
                width=5
            ),
            dbc.Col(
                dcc.Graph(
                    id='scatter-plot',
                    clear_on_unhover=True
                ),
                width=7
            )
        ]),
        dcc.Tooltip(id='tooltip'),

        dbc.Row(dbc.Col(html.Br()))
    ])

    return app
