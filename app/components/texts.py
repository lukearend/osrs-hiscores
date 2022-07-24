""" Textual content """
import os

import dash_bootstrap_components as dbc
from dash import html, dcc

from app.helpers import assets_dir, load_icon_b64


def page_title():
    text = "OSRS hiscores explorer"
    return html.H1(text, className='title-text')


def info_blurb():
    hiscores_link = dcc.Link(
        "Old School Runescape hiscores",
        href='https://secure.runescape.com/m=hiscore_oldschool/overall',
        target='_blank'  # open link in new tab
    )
    download_link = dcc.Link(
        "available for download",
        href='https://bit.ly/osrs-hiscores-dataset',
        target='_blank'
    )
    content = [
        """Each point represents a cluster of OSRS players with similar stats.
        The closer two clusters are, the more similar are the accounts in each
        of those two clusters. The size of each point corresponds to the number
        of players in that cluster. Axes have no meaningful interpretation. Player
        stats were downloaded from the """, hiscores_link, """ on July 21, 2022.
        The dataset is """, download_link, """ in CSV format from Google Drive."""
    ]
    return dbc.Col(content, className='info-text')


def link_button(text: str, href: str, icon: str):
    icon = html.Img(
        src='data:image/png;base64,' + load_icon_b64(icon),
        className='table-icon img-center',
        style={'height': '1em', 'padding-top': 0},
    )
    return dbc.Button(
        dbc.Row(
            [
                dbc.Col(icon, width='auto'),
                dbc.Col(text),
            ],
            align='center',
            className='gx-1'
        ),
        href=href,
        className='support-button',
        target='_blank'
    )


def top_buttons():
    github = link_button(
        "project homepage",
        href='https://github.com/lukearend/osrs-hiscores',
        icon=os.path.join(assets_dir(), 'github.png')
    )
    coffee = link_button(
        "buy me a coffee",
        href='https://www.buymeacoffee.com/snakeylime',
        icon=os.path.join(assets_dir(), 'coffee.png')
    )
    return dbc.Row(
        [
            dbc.Col(github, width='auto'),
            dbc.Col(coffee, width='auto')
        ],
        align='center',
        justify='end',
        className='gx-3'
    )


def watermark():
    msg = html.Div(f"made with ❤️ and ☕ by snakeylime", className='support-link')
    return dbc.Row(dbc.Col(msg, width='auto'), justify='end')
