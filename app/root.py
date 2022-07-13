""" Base application container. """

import dash_bootstrap_components as dbc
from app.containers import header, footer, lookup, controls, scatterplot, tables, boxplot, store

def root_layout():
    device = 'phone'
    # device = 'desktop'
    # device = 'tablet'

    if device == 'phone':
        body = dbc.Col([
            lookup(),
            tables(),
            controls(),
            scatterplot(),
            boxplot(),
        ])
    else:
        lcol = dbc.Col([
            lookup(),
            tables(),
            boxplot(),
        ])
        rcol = dbc.Col([
            controls(),
            scatterplot(),
        ])
        body = dbc.Row([lcol, rcol])

    root = [
        header(),
        body,
        footer(),
        store(),
    ]

    return dbc.Container([
        dbc.Row(dbc.Col(c)) for c in root
    ])
