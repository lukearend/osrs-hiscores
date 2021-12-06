import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash

from app import get_level_marks, skill_pretty
from app.figures import get_scatterplot, get_boxplot


def build_layout(appdata)
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

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
                                    id='split-dropdown',
                                    options=[
                                        {'label': 'All skills','value': 'all'},
                                        {'label': 'Combat skills','value': 'cb'},
                                        {'label': 'Non-combat skills','value': 'noncb'},
                                    ],
                                    value='all' ,
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
                                        {'label': skill_pretty(skill),
                                         'value': skill} for skill in skills
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
                        figure=get_scatterplot(appdata['all'], 'total', [1, 2277]),
                        style={'height': '80vh'},
                        clear_on_unhover=True
                    ),
                    html.Br()
                ]
            )
        ),
        dcc.Tooltip(id='tooltip'),

        dbc.Row(
            dbc.Col(
                [
                    dcc.Box(
                        id='box-plot',
                        figure=get_boxplot(appdata['all']['percentiles'], 1000)
                    ),
                    html.Br()
                ]
            )
        )
    ])

    return app
