from typing import Dict, Any

import dash_bootstrap_components as dbc
from dash import html, Output, Input

from app import app, styles
from app.helpers import load_icon_b64, load_table_layout
from src.common import osrs_skills


OSRS_SKILLS = osrs_skills(include_total=True)


def stats_table(id: str, title_id: str, store_id: str):
    table_skills = load_table_layout()

    elems = []
    for row_i, row_skills in enumerate(table_skills):
        row = []
        for col_i, skill in enumerate(row_skills):
            icon = html.Img(
                src='data:image/png;base64,' + load_icon_b64(skill),
                title=skill.capitalize(),
                height=styles.TABLE_ICON_HEIGHT,
            )
            stat_container = html.Div(id=f'{id}:{skill}'),
            elem = (icon, stat_container)
            row.append(elem)

        elems.append(row)

    skills = [skill for row in table_skills for skill in row]

    @app.callback(
        *[Output(f'{id}:{skill}', 'children') for skill in skills],
        Input(store_id, 'data'),
    )
    def update_stats(stats_dict: Dict[str, Any]) -> str:
        if not stats_dict:
            return ['' for _ in skills]
        return [
            str(stats_dict[skill]) if skill in stats_dict else ''
            for skill in skills
        ]

    # Lay out table as a row of columns so the cells always stack vertically.
    cols = []
    for col_i in range(3):
        col_cells = []
        for row_i in range(8):
            icon, stat = elems[row_i][col_i]
            icon = dbc.Col(
                icon,
                # width=4,
                # className='table-icon',
            )
            stat = dbc.Col(
                stat,
                # width=8,
                # className='table-stat',
            )
            cell = dbc.Row(
                [
                    icon,
                    stat,
                ],
                style={
                    # 'color': styles.TABLE_CELL,
                },
                # className='stats-table-cell',
            )
            col_cells.append(cell)

        col = dbc.Col(
            col_cells,
            # className='stats-table-col',
            width='auto'
        )
        cols.append(col)

    table = dbc.Row(
        cols,
        style={
            # 'color': styles.TABLE_BG,
        },
        # className='stats-table',
    )
    title = html.Div(id=title_id)
    return dbc.Col(
        [
            title,
            table
        ],
        # className='table-container',
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
