import textwrap
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
    heart = '&#10084'
    coffee = '&#9749'
    text = dcc.Markdown(f"made with {heart} and {coffee} by snakeylime")
    button = dbc.Button("buy me a coffee", href=link)
    return dbc.Row([
        dbc.Col(text),
        dbc.Col(button),
    ])


def github_link():
    link = 'https://github.com/lukearend/osrs-hiscores'
    text = f"Check out the [source code]({link}) on Github"
    return dcc.Markdown(text)


def download_link():
    link = 'https://drive.google.com/drive/u/0/folders/***REMOVED***'
    text = f"[Download the dataset]({link}) from Google Drive"
    return dcc.Markdown(text)
