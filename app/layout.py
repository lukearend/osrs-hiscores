

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from app import format_skill, get_level_tick_marks, get_color_range, \
    get_color_label, get_point_size, load_params, load_app_data, load_table_layout
from app.plotdata import compute_scatterplot_data
from app.figures import get_empty_boxplot, get_scatterplot
from src.analysis import osrs_skills


def build_layout() -> Dash:
    app = Dash(__name__, title="OSRS player clusters", external_stylesheets=[dbc.themes.BOOTSTRAP])

    init_split = 'all'
    init_skill = 'total'
    init_ptsize = 'small'
    init_level_range = [1, 2277]
    init_n_neighbors = load_params()['n_neighbors'][0]
    init_min_dist = load_params()['min_dist'][0]
    init_k = load_params()['k'][0]

    app_data = load_app_data(init_k, init_n_neighbors, init_min_dist)

    app.layout = dbc.Container([
        dbc.Row(
            dbc.Col([
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
            ])
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
                                    value=init_split,
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
                                        {'label': format_skill(init_skill), 'value': skill}
                                        for skill in osrs_skills(include_total=True)
                                    ],
                                    value=init_skill,
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
                                html.Div(children="# clusters:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='kmeans-k',
                                    options=[
                                        {'label': str(n), 'value': n}
                                        for n in load_params()['k']
                                    ],
                                    value=init_k,
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=4
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(children="# neighbors:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='n-neighbors',
                                    options=[
                                        {'label': str(n), 'value': n}
                                        for n in load_params()['n_neighbors']
                                    ],
                                    value=init_n_neighbors,
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=4
                ),
                dbc.Col(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(children="min dist:"),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id='min-dist',
                                    options=[
                                        {'label': f'{d:.2f}', 'value': d}
                                        for d in load_params()['min_dist']
                                    ],
                                    value=init_min_dist,
                                    clearable=False
                                )
                            )
                        ],
                        align='center'
                    ),
                    width=4
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
                        min=init_level_range[0],
                        max=init_level_range[1],
                        step=1,
                        value=init_level_range,
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
                                    maxLength=12,
                                    debounce=True
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
                                    value=init_ptsize,
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
                                build_level_table(name='player-table'),
                            ]),
                            dbc.Col([
                                html.Strong(id='cluster-table-title'),
                                build_level_table(name='cluster-table')
                            ]),
                        ],
                        align='center'
                    ),

                    html.Br(),
                    dbc.Row(
                        dbc.Col([
                            html.Div(id='box-plot-text'),
                            dcc.Graph(
                                id='box-plot',
                                style={'height': '20vh'},
                                figure=get_empty_boxplot(init_split)
                            )
                        ]),
                        align='center'
                    )
                ],
                width=5
            ),
            dbc.Col(
                dcc.Graph(
                    id='scatter-plot',
                    clear_on_unhover=True,
                    figure=get_scatterplot(
                        df=compute_scatterplot_data(app_data[init_split], init_skill, init_level_range),
                        colorlims=get_color_range(init_skill),
                        colorlabel=get_color_label(init_skill),
                        pointsize=get_point_size(init_ptsize),
                        axlims=app_data[init_split].xyz_axlims
                    ),
                ),
                width=7
            )
        ]),
        dcc.Tooltip(id='tooltip'),

        dbc.Row(dbc.Col(html.Br()))
    ])

    return app


def build_level_table(name: str) -> dbc.Col:
    skills_layout = load_table_layout()

    table_rows = []
    for skill_row in skills_layout:

        table_row = []
        for skill in skill_row:
            icon = html.Div(html.Img(src=f'/assets/icons/{skill}_icon.png'))
            value = html.Div(id=f'{name}-{skill}')

            table_elem = dbc.Row(
                [
                    dbc.Col(icon, width=6),
                    dbc.Col(value, width=6)
                ],
                align='center',
                justify='center',
                className='g-1'  # almost no gutter between icon and number
            )
            table_row.append(dbc.Col(table_elem, width=4))

        table_rows.append(dbc.Row(table_row, align='center'))

    return dbc.Col(table_rows)
