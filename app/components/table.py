from typing import Dict, Any

import dash_bootstrap_components as dbc
from dash import html, Output, Input

from app import app
from app import styles
from app.helpers import load_icon_b64, load_table_layout


def stats_table(id: str, title_id: str, store_id: str):
    table_skills = load_table_layout()

    elems = []
    for row_i, row_skills in enumerate(table_skills):
        row = []
        for col_i, skill in enumerate(row_skills):
            icon = html.Img(
                src='data:image/png;base64,' + load_icon_b64(skill),
                title=skill.capitalize(),
                className='table-icon img-center',
                style={
                    'padding-top': 0,
                    'padding-bottom': 0,
                },
                # height=styles.TABLE_ICON_HEIGHT,
            )
            stat_container = html.Div(
                id=f'{id}:{skill}',
                className='table-stat',
                style={
                    'white-space': 'pre',  # prevents collapsing whitespace
                }
            ),
            elem = (icon, stat_container)
            row.append(elem)

        elems.append(row)

    skills = [skill for row in table_skills for skill in row]

    @app.callback(
        *[Output(f'{id}:{skill}', 'children') for skill in skills],
        Input(store_id, 'data'),
    )
    def update_stats(stats_dict: Dict[str, int]) -> str:
        if not stats_dict:
            return ['' for _ in skills]
        outs = []
        for skill in skills:
            if skill not in stats_dict:
                txt = ' '
            else:
                lvl = stats_dict[skill]
                if lvl == 0:
                    txt = '-'
                elif skill == 'total':
                    txt = dbc.Col([
                        dbc.Row(dbc.Col('Total:', className='g-0',
                                style={'padding-top': 0,
                                       'padding-bottom': 0}), className='g-0'),
                        dbc.Row(dbc.Col(str(lvl), className='g-0',
                                style={'padding-top': 0,
                                       'padding-bottom': 0}), className='g-0'),
                    ], className='g-0', style={'font-size': '50%'})
                else:
                    txt = str(lvl)
            outs.append(txt)
        return outs

    cols = []
    for j in range(3):
        col = []
        for i in range(8):
            icon, stat = elems[i][j]
            icon = dbc.Col(
                icon,
                width=4,
                className='table-icon'
            )
            stat = dbc.Col(
                stat,
                width=8,
            )
            elem = dbc.Row(
                [icon, stat],
                className='table-cell',
                style={
                    'background-color': styles.TABLE_CELL_COLOR,
                    'border-color': styles.TABLE_BORDER_COLOR,
                }
            )
            col.append(elem)

        col = dbc.Col(col)
        cols.append(col)

    header = dbc.Row(dbc.Col(html.Div(id=title_id)))
    body = dbc.Row(cols)
    return dbc.Col(
        [header, body],
        className='stats-table',
        style={
            'background-color': styles.TABLE_BG_COLOR,
            'border-color': styles.TABLE_BORDER_COLOR,
        },
    )


def cluster_stats_table():
    return stats_table(
        id='cluster-table',
        title_id='cluster-table-title',
        store_id='cluster-table-data',
    )


def player_stats_table():
    return stats_table(
        id='player-table',
        title_id='player-table-title',
        store_id='player-table-data',
    )


def stats_tables():
    return dbc.Row(
        [
            dbc.Col(
                player_stats_table(),
                width='auto',
            ),
            dbc.Col(
                cluster_stats_table(), width='auto',
            ),
        ],
    )
