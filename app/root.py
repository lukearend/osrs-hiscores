from app.components.text import *
import dash_bootstrap_components as dbc


def header():
    return dbc.Col([
        page_title(),
        info_blurb(),
    ])

def body():
    return dbc.Col([
    ])

def footer():
    return dbc.Col([
        support_link(),
        github_link(),
        download_link(),
    ])

def root_layout():
    return dbc.Container([
        dbc.Row(header()),
        dbc.Row(body()),
        dbc.Row(footer()),
    ])
