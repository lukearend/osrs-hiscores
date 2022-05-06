""" Static layout of application page. """

from typing import Dict

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from dash_extensions import EventListener

from src import osrs_skills
from src.data.types import SplitResults
from src.app.helpers import load_table_layout, format_skill, \
    get_level_tick_marks, get_color_label, get_point_size, load_skill_icon
from src.app.plotdata import scatterplot_data
from src.app.figures import get_empty_boxplot, get_scatterplot


INIT_SPLIT = 'all'
INIT_SKILL = 'total'
INIT_PTSIZE = 'small'

LEFT_PANEL_WIDTH = 4


def build_layout(app: Dash, app_data: Dict[str, SplitResults]):

    init_tickmarks = get_level_tick_marks(INIT_SKILL)
    init_lvlrange = (init_tickmarks[0], init_tickmarks[-1])

    app.title = "OSRS account clusters"
    app.layout = dbc.Container([

        html.Br(),

        # Frontmatter
        dbc.Row(dbc.Col(html.H1(html.Strong("OSRS account clusters")))),
        dbc.Row(dbc.Col(html.Div("""
            Each point represents a cluster of OSRS players with
            similar stats. The closer two clusters are, the more
            similar the accounts are in each of those two clusters.
            The size of each point corresponds to the number of players
            in that cluster. Axes have no meaningful interpretation.
        """))),
        html.Br(),

        dbc.Row([

            # Left panel
            dbc.Col([

                # Username input box
                dcc.Store(id='current-player'),
                dbc.Row([
                    dbc.Col(html.Div(children="Lookup player:"), width='auto'),
                    dbc.Col(dcc.Input(
                        id='username-text',
                        type='text',
                        placeholder="e.g. 'snakeylime'",
                        maxLength=12,
                        debounce=True
                    ), width='auto'),
                ], align='center'),
                html.Br(),

                dcc.Store(id='query-event'),
                dbc.Col(html.Div(id='player-query-text')),
                html.Br(),

                # Player/cluster stats tables
                dbc.Row([
                    dbc.Col(html.Strong(id='player-table-title'), ),
                    dbc.Col(html.Strong(id='cluster-table-title'), ),
                ], align='center', className='g-5'),
                dbc.Row([
                    dbc.Col(build_level_table(name='player-table'), ),
                    dbc.Col(build_level_table(name='cluster-table')),
                ], align='center', className='g-5'),
                html.Br(),

                # Boxplot
                dbc.Row(dbc.Col([
                    html.Div(id='box-plot-text'),
                    dcc.Graph(
                        id='box-plot',
                        style={'height': '20vh'},
                        figure=get_empty_boxplot(INIT_SPLIT, app_data[INIT_SPLIT].skills)
                    )
                ]), align='center'),
                html.Br()

            ], lg=LEFT_PANEL_WIDTH),  # allow left/right panels to wrap on smaller screens

            # Right panel
            dbc.Col([

                # Cluster-by and color-by dropdowns
                dbc.Row([

                    dbc.Col(dbc.Row([
                        dbc.Col(html.Div(children="Cluster by:"), width='auto'),
                        dbc.Col(dcc.Dropdown(
                            id='current-split',
                            options=[
                                {'label': 'All skills', 'value': 'all'},
                                {'label': 'Combat skills', 'value': 'cb'},
                                {'label': 'Non-combat skills', 'value': 'noncb'},
                            ],
                            value=INIT_SPLIT,
                            clearable=False
                        ))
                    ], align='center', className='g-2')),  # small gutter between text and dropdown

                    dbc.Col(dbc.Row([
                        dbc.Col(html.Div(children="Color by:"), width='auto'),
                        dbc.Col(dcc.Dropdown(
                            id='current-skill',
                            options=[
                                {'label': format_skill(INIT_SKILL), 'value': skill}
                                for skill in osrs_skills(include_total=True)
                            ],
                            value=INIT_SKILL,
                            clearable=False
                        ))
                    ], align='center', className='g-2'))

                ], align='center'),

                # Level slider and point size
                dbc.Row([

                    dbc.Col(dbc.Row([
                        dbc.Col(html.Div(children="Level range:"), width='auto'),
                        dbc.Col(dcc.RangeSlider(
                            id='level-range',
                            min=init_lvlrange[0],
                            max=init_lvlrange[-1],
                            step=1,
                            value=(init_lvlrange[0], init_lvlrange[-1]),
                            tooltip={'placement': 'bottom'},
                            allowCross=False,
                            marks={i: str(i) for i in get_level_tick_marks('total')}
                        ), style={'padding-top': '2vh'})  # padding aligns slider vertically
                    ], align='center', className='g-0')),

                    dbc.Col(dbc.Row([
                        dbc.Col(html.Div(children="Point size:"), width='auto'),
                        dbc.Col(dcc.Dropdown(
                            id='point-size',
                            options=[{'label': s, 'value': s} for s in ['small', 'medium', 'large']],
                            value=INIT_PTSIZE,
                            clearable=False
                        ))
                    ], align='center', className='g-2'), width=3),

                ], align='center', className='g-0'),  # no gutter since level slider adds horizontal space

                # Scatterplot
                dcc.Store(id='current-cluster'),
                dcc.Store(id='clicked-cluster'),
                dcc.Tooltip(id='tooltip'),
                dbc.Col(EventListener(
                    id='click-listener',  # detect clicks anywhere on the main figure
                    events=[{'event': 'mousedown', 'props': ['x', 'y']}],
                    children=[dcc.Graph(
                        id='scatter-plot',
                        clear_on_unhover=True,
                        figure=get_scatterplot(
                            df=scatterplot_data(app_data[INIT_SPLIT], INIT_SKILL, init_lvlrange),
                            colorbar_ticks=get_level_tick_marks(INIT_SKILL),
                            colorbar_label=get_color_label(INIT_SKILL),
                            size_factor=get_point_size(INIT_PTSIZE),
                            axis_limits=app_data[INIT_SPLIT].xyz_axlims
                        )
                    )]
                ))

            ], align='center', lg=12 - LEFT_PANEL_WIDTH)

        ], className='g-5'),

        html.Br()
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
                justify='center'
            )
            table_row.append(dbc.Col(table_elem, width=4))
        table_rows.append(dbc.Row(table_row, align='center'))
    return dbc.Col(table_rows)
