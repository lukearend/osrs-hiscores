import dash_bootstrap_components as dbc
from dash import html, dcc

from app.components.boxplot import boxplot_title, boxplot
from app.components.blobs import username_blobs
from app.components.dropdowns import dropdown_menus
from app.components.input import username_input
from app.components.store import store_vars
from app.components.table import stats_tables
from app.components.playertxt import focused_player


def page_title():
    text = "OSRS hiscores explorer"
    text = html.Strong(text)
    return html.H1(text)


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
    return dbc.Col(content)


def github_link():
    source_code = dcc.Link(
        "source code",
        href='https://github.com/lukearend/osrs-hiscores',
        target='_blank',
    )
    content = ["Want to dig deeper? Check out the ", source_code, " on Github."]
    return dbc.Col(content)


def download_link():
    available = dcc.Link(
        "available for download",
        href='https://drive.google.com/drive/u/0/folders/***REMOVED***',
        target='_blank',
    )
    content = ["The dataset is ", available, " in CSV format from Google Drive."]
    return dbc.Col(content)


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


def root_layout():
    root = [
        page_title(),
        info_blurb(),
        html.Br(),
        username_input(),
        html.Br(),
        username_blobs(),
        focused_player(),
        dropdown_menus(),
        html.Br(),
        stats_tables(),
        html.Br(),
        boxplot_title(),
        boxplot(),
        html.Br(),
        github_link(),
        download_link(),
        html.Hr(),
        support_msg(),
        html.Br(),
        store_vars(),
    ]
    return dbc.Container([
        dbc.Row(dbc.Col(i))
        for i in root
    ])
