import textwrap

from app.components.blobs import username_blobs
from app.components.input import username_input
from app.components.store import store_vars

import dash_bootstrap_components as dbc
from dash import html, dcc


def page_title():
    text = "OSRS hiscores explorer"
    text = html.Strong(text)
    text = html.H1(text)
    return dbc.Col(text)


def info_blurb():
    link = 'https://secure.runescape.com/m=hiscore_oldschool/overall'
    text = textwrap.dedent(f"""
        Each point represents a cluster of OSRS players with similar stats. The
        closer two clusters are, the more similar are the accounts in each of
        those two clusters. The size of each point corresponds to the number
        of players in that cluster. Axes have no meaningful interpretation.
        Player stats were downloaded from the [Old School Runescape hiscores]
        ({link}) in April 2022.
    """)
    text = dcc.Markdown(text)
    return dbc.Col(text)


def support_link():
    link = 'https://www.buymeacoffee.com/snakeylime'
    text = html.Div(
        f"made with ❤️ and ☕ by snakeylime",
        className='support-link',
    )
    button = dbc.Button(
        "buy me a coffee",
        href=link,
        target='_blank',  # open link in new tab
        className='support-button',
    )
    return dbc.Row(
        [
            dbc.Col(text, width='auto'),
            dbc.Col(button, width='auto'),
        ],
        align='center',
        justify='end',
    )


def github_link():
    link = 'https://github.com/lukearend/osrs-hiscores'
    text = f"Want to dig deeper? Check out the [source code]({link}) on Github."
    return dcc.Markdown(text)


def download_link():
    link = 'https://drive.google.com/drive/u/0/folders/***REMOVED***'
    text = f"The dataset is [available for download]({link}) in CSV format from Google Drive."
    return dcc.Markdown(text)


def root_layout():
    frontmatter = dbc.Col([
        page_title(),
        info_blurb(),
    ])

    endmatter = dbc.Col([
        github_link(),
        download_link(),
        html.Hr(),
        support_link(),
    ])

    body = dbc.Col([
        username_input(),
        username_blobs(),
    ])

    return dbc.Container(
        [
            frontmatter,
            html.Br(),
            body,
            html.Br(),
            endmatter,
            store_vars(),
        ]
    )
