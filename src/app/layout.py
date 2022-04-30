""" Static layout of application page. """

from typing import Dict

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from src import osrs_skills
from src.data.types import SplitResults
from src.app.helpers import load_table_layout, format_skill, \
    get_level_tick_marks, get_color_range, get_color_label, get_point_size, load_skill_icon
from src.app.plotdata import scatterplot_data
from src.app.figures import get_empty_boxplot, get_scatterplot


INIT_SPLIT = 'all'
INIT_SKILL = 'total'
INIT_PTSIZE = 'small'
INIT_LEVEL_RANGE = [1, 2277]


def build_layout(app: Dash, app_data: Dict[str, SplitResults]):

    app.title = "OSRS account clusters"
    app.layout = dbc.Container([
        dbc.Row(
            dbc.Col([
                html.Br(),
                html.H1(children=html.Strong('OSRS account clusters')),
                html.Div(children='''
                    Each point represents a cluster of OSRS players with
                    similar stats. The closer two clusters are, the more
                    similar the accounts are in each of those two clusters.
                    The size of each point corresponds to the number of players
                    in that cluster. Axes have no meaningful interpretation.
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
                                    value=INIT_SPLIT,
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
                                        {'label': format_skill(INIT_SKILL), 'value': skill}
                                        for skill in osrs_skills(include_total=True)
                                    ],
                                    value=INIT_SKILL,
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
                        min=INIT_LEVEL_RANGE[0],
                        max=INIT_LEVEL_RANGE[1],
                        step=1,
                        value=INIT_LEVEL_RANGE,
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
                                    placeholder="e.g. 'snakeylime'",
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
                                    value=INIT_PTSIZE,
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
                                figure=get_empty_boxplot(INIT_SPLIT, app_data[INIT_SPLIT].skills)
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
                    figure=get_scatterplot(
                        df=scatterplot_data(app_data[INIT_SPLIT], INIT_SKILL, INIT_LEVEL_RANGE),
                        colorbar_limits=get_color_range(INIT_SKILL),
                        colorbar_label=get_color_label(INIT_SKILL),
                        size_factor=get_point_size(INIT_PTSIZE),
                        axis_limits=app_data[INIT_SPLIT].xyz_axlims
                    ),
                ),
                width=7
            )
        ]),
        dcc.Tooltip(id='tooltip'),

        dbc.Row(dbc.Col(html.Br()))
    ])


def build_level_table(name: str) -> dbc.Col:

    skills_layout = load_table_layout()
    table_rows = []
    for skill_row in skills_layout:
        table_row = []
        for skill in skill_row:
            icon = html.Img(src=load_skill_icon(skill), title=skill.capitalize())
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
