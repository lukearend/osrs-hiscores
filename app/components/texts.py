""" Textual content """

import dash_bootstrap_components as dbc
from dash import html, dcc


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