""" Static layout of application page. """

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from app import load_table_layout, format_skill, get_level_tick_marks, get_color_range, get_color_label, get_point_size
from app.plotdata import compute_scatterplot_data
from app.figures import get_empty_boxplot, get_scatterplot
from src.analysis import osrs_skills


def build_layout(app_data) -> Dash:
    app = Dash(__name__, title="OSRS player clusters", external_stylesheets=[dbc.themes.BOOTSTRAP])

    init_split = 'all'
    init_skill = 'total'
    init_ptsize = 'small'
    init_level_range = [1, 2277]

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
        dcc.Store(id='clicked-cluster'),
        dcc.Store(id='last-clicked-ts'),
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
                                figure=get_empty_boxplot(init_split, app_data[init_split].skills)
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
                        colorbar_limits=get_color_range(init_skill),
                        colorbar_label=get_color_label(init_skill),
                        size_factor=get_point_size(init_ptsize),
                        axis_limits=app_data[init_split].xyz_axlims
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
                className='g-1'  # very small gutter between icon and number
            )
            table_row.append(dbc.Col(table_elem, width=4))

        table_rows.append(dbc.Row(table_row, align='center'))

    return dbc.Col(table_rows)
