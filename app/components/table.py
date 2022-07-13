""" Tables containing player/cluster stats for all skills. """

from typing import Dict, Any, Callable

import dash_bootstrap_components as dbc
from dash import html, Output, Input, no_update

from app import app
from app import styles
from app.helpers import load_icon_b64, load_table_layout


def stats_table(id: str, store_id: str, title_fmt_fn: Callable):
    title = html.Div(
        id=f'{id}:title',
        className='label-text',
    )

    table_skills = load_table_layout()
    elems = []
    for row_i, row_skills in enumerate(table_skills):
        row = []
        for col_i, skill in enumerate(row_skills):
            icon = html.Img(
                src='data:image/png;base64,' + load_icon_b64(skill),
                title=skill.capitalize(),
                className='table-icon img-center',
            )
            stat_container = html.Div(
                id=f'{id}:{skill}',
                style={
                    'white-space': 'pre',  # prevents collapsing whitespace
                }
            )
            elem = (icon, stat_container)
            row.append(elem)
        elems.append(row)
    skills = [skill for row in table_skills for skill in row]

    # Table title is produced by applying format function to the title data.
    @app.callback(
        Output(f'{id}:title', 'children'),
        Input(f'{store_id}:title', 'data'),
    )
    def update_title(title_data: Any) -> str:
        return title_fmt_fn(title_data)

    # Table stats are updated as individual outputs in one big callback.
    @app.callback(
        *[Output(f'{id}:{skill}', 'children') for skill in skills],
        Input(f'{store_id}:stats', 'data'),
        prevent_initial_call=True,
    )
    def update_stats(stats_dict: Dict[str, Any]) -> str:
        if stats_dict is None:
            return no_update

        stats = []
        for skill in skills:
            if skill not in stats_dict:
                stats.append(' ')
                continue
            lvl = stats_dict[skill]
            txt = '-' if lvl is None else str(lvl)
            stats.append(txt)

        return tuple(stats)

    table_cols = []
    for j in range(3):
        col_elems = []
        for i in range(8):
            icon, stat = elems[i][j]
            icon_col = dbc.Col(
                icon,
                width=4,
            )
            stat_col = dbc.Col(
                stat,
                width=8,
            )
            icon_stat = dbc.Row(
                [icon_col, stat_col],
            )
            col_elems.append(icon_stat)

        col = dbc.Col(
            col_elems,
        )
        table_cols.append(col)

    table = dbc.Row(
        table_cols,
        style={
            'background-color': styles.TABLE_BG_COLOR,
        },
        className='stats-table g-1',
    )
    return dbc.Col(
        [
            title,
            table,
        ],
    )


def cluster_stats_table():

    def title_fn(clusterid: int) -> str:
        if clusterid is None:
            return "Cluster stats"
        return f"Cluster {clusterid} stats"

    return stats_table(
        id='cluster-table',
        store_id='cluster-table-data',
        title_fmt_fn=title_fn,
    )


def player_stats_table():

    def title_fn(username: str) -> str:
        if username is None:
            return "Player stats"
        return f"‘{username}' stats"  # true opening single quote char needed for bold font

    return stats_table(
        id='player-table',
        store_id='player-table-data',
        title_fmt_fn=title_fn,
    )
