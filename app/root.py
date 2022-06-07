from app.components.input import *
from app.components.text import *
import dash_bootstrap_components as dbc


def header():
    return dbc.Col([
        page_title(),
        info_blurb(),
    ])

def body():
    username_input = UsernameInput()
    return dbc.Col([
        username_input.layout(),
    ])

def footer():
    return dbc.Col([
        github_link(),
        download_link(),
        html.Hr(),
        support_link(),
    ])

def root_layout():
    return dbc.Container([
        dbc.Row(header()),
        dbc.Row(dbc.Col(html.Br())),
        dbc.Row(body()),
        dbc.Row(dbc.Col(html.Br())),
        dbc.Row(footer()),
    ])
