import dash_bootstrap_components as dbc
from dash import html, dcc

from app.components.boxplot import boxplot_title, boxplot
from app.components.blobs import username_blobs
from app.components.dropdowns import split_menu, point_size_menu, color_by_menu
from app.components.input import username_input
from app.components.scatterplot import scatterplot
from app.components.slider import level_range_slider
from app.components.store import store_vars
from app.components.table import stats_tables
from app.components.playertxt import focused_player
from app.components.space import vspace, vspace_if_nonempty


def page_title():
    text = "OSRS hiscores explorer"
    return html.H1(
        text,
        className='title-text',
    )


def info_blurb():
    osrs_hiscores = dcc.Link(
        "Old School Runescape hiscores",
        href='https://secure.runescape.com/m=hiscore_oldschool/overall',
        target='_blank',  # open link in new tab
    )
    content = [
        """Each point represents a cluster of OSRS players with similar stats.
        The closer two clusters are, the more similar are the accounts in each 
        of those two clusters. The size of each point corresponds to the number
        of players in that cluster. Axes have no meaningful interpretation.
        Player stats were downloaded from the """, osrs_hiscores, " in April 2022.",
    ]
    return dbc.Col(
        content,
        className='info-text',
    )


def github_link():
    project_page = dcc.Link(
        "project homepage",
        href='https://github.com/lukearend/osrs-hiscores',
        target='_blank',
    )
    content = ["Want to dig deeper? Check out the ", project_page, " on Github."]
    return dbc.Col(
        content,
        className='info-text',
    )


def download_link():
    available = dcc.Link(
        "available for download",
        href='https://drive.google.com/drive/u/0/folders/***REMOVED***',
        target='_blank',
    )
    content = ["The dataset is ", available, " in CSV format from Google Drive."]
    return dbc.Col(
        content,
        className='info-text',
    )


def support_msg():
    text = html.Div(
        f"made with ❤️ and ☕ by snakeylime",
        className='support-link',
    )
    button = dbc.Button(
        "buy me a coffee",
        href='https://www.buymeacoffee.com/snakeylime',
        className='support-button',
        target='_blank',
    )
    return dbc.Row(
        [
            dbc.Col(text, width='auto'),
            dbc.Col(button, width='auto'),
        ],
        align='center',
        justify='end',
    )


def scatterplot_controls():
    return dbc.Row(
        [
            dbc.Col(split_menu(), width='auto'),
            dbc.Col(point_size_menu(), width='auto'),
            dbc.Col(color_by_menu(), width='auto'),
            dbc.Col(level_range_slider()),
        ],
        align='center',
    )


def root_layout():
    body = [
        username_input(),
        vspace(),
        username_blobs(),
        vspace_if_nonempty(id='current-players'),
        focused_player(),
        vspace_if_nonempty(id='focused-player', n=2),
        scatterplot_controls(),
        scatterplot(),
        vspace(),
        stats_tables(),
        vspace(),
        boxplot_title(),
        boxplot(),
    ]

    root = [
        vspace(),
        page_title(),
        info_blurb(),
        vspace(n=2),
        body,
        vspace(n=2),
        github_link(),
        download_link(),
        html.Hr(),
        support_msg(),
        vspace(),
        store_vars(show=[]),
    ]

    return dbc.Container([
        dbc.Row(dbc.Col(elem))
        for elem in root
    ])
