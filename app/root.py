import textwrap

import dash_bootstrap_components as dbc
from dash import html, dcc


def page_title():
    title_text = "OSRS hiscores explorer"
    title_bold = html.Strong(title_text)
    return html.H1(
        title_bold)

def info_blurb():
    blurb_text = textwrap.dedent("""
        Each point represents a cluster of OSRS players with similar stats. The
        closer two clusters are, the more similar are the accounts in each of
        those two clusters. The size of each point corresponds to the number
        of players in that cluster. Axes have no meaningful interpretation.
        Player stats were downloaded from the [Old School Runescape hiscores]
        (https://secure.runescape.com/m=hiscore_oldschool/overall) in April 2022.
    """)
    return dcc.Markdown(blurb_text)

# def github_link():
#     text1 = "Like what you see? "
#     link = dcc.Link(
#         "Buy me a coffee", 'https://www.buymeacoffee.com/snakeylime'
#     )
#     text2 = " to help cover cloud hosting fees."
#     "Want to dig deeper? Check out the "on Github."
#     link = dcc.Link(
#         "source code", 'https://github.com/lukearend/osrs-hiscores'
#     )

def header():
    return dbc.Col([
        page_title(),
        info_blurb()
    ])

def footer():
    return dbc.Col([
    ])

def root_layout():
    return dbc.Container([
        header(),
        footer(),
    ])


# class MainApp:
#     def __init__(self):
#         self.backend = Backend(self.app, self.app_data)
#         self.datastore = self.backend.store
#
#         self.uname_input = UsernameInput(self.app, self.app_data, self.datastore)
#         self.split_menu = SplitMenu(self.app, self.app_data, self.datastore)
#         self.ptsize_menu = PointSizeMenu(self.app, self.app_data, self.datastore)
#         self.boxplot = Boxplot(self.app, self.app_data, self.datastore)
#
#     def build_layout(self):
#         storevars = []
#         for field in fields(self.datastore):
#             var = getattr(self.datastore, field.name)
#             storevars.append(var)
#
#         uname_input = dbc.Row([
#                 dbc.Col(self.uname_input.label, width='auto'),
#                 dbc.Col(self.uname_input.input),
#             ],
#             align='center',
#         )
#         split_menu = dbc.Row([
#                 dbc.Col(self.split_menu.label, width='auto'),
#                 dbc.Col(self.split_menu.dropdown),
#             ],
#             align='center',
#         )
#         ptsize_menu = dbc.Row([
#                 dbc.Col(self.ptsize_menu.label, width='auto'),
#                 dbc.Col(self.ptsize_menu.dropdown),
#             ],
#             align='center',
#         )
#         controls = dbc.Row(
#             [
#                 dbc.Col(split_menu, width='auto'),
#                 dbc.Col(ptsize_menu),
#             ],
#             align='center',
#         )
#         boxplot = dbc.Col([
#             self.boxplot.title,
#             self.boxplot.graph,
#         ])
#
#         self.app.layout = dbc.Container([
#             dbc.Row(dbc.Col(storevars)),
#             dbc.Row(dbc.Col(uname_input)),
#             dbc.Row(dbc.Col(controls)),
#             dbc.Row(dbc.Col(boxplot)),
#             dbc.Row(self.backend.view)
#         ])
#
#     def add_callbacks(self):
#         self.backend.add_callbacks()
#         self.uname_input.add_callbacks()
#         self.split_menu.add_callbacks()
#         self.ptsize_menu.add_callbacks()
#         self.boxplot.add_callbacks()
