from dataclasses import dataclass, fields
from typing import OrderedDict, Tuple

from dash import Dash, Output, Input, dcc, html

from prevent_initial_call.types import SplitResults


@dataclass
class DataStore:
    currentsplit: dcc.Store
    boxplot_clusterid: dcc.Store
    boxplot_nplayers: dcc.Store
    scatterplot_ptsize: dcc.Store


class Backend:
    """ Behind-the-scenes queries and data manipulation. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults]):
        self.app = app
        self.app_data = app_data
        self.store = DataStore(
            currentsplit=dcc.Store('current-split'),
            boxplot_clusterid=dcc.Store('boxplot-clusterid'),
            boxplot_nplayers=dcc.Store('boxplot-nplayers'),
            scatterplot_ptsize=dcc.Store('scatterplot-ptsize'),
        )
        self.view = html.Div(children=[])

    def add_callbacks(self):

        @self.app.callback(
            Output(self.store.boxplot_clusterid, 'data'),
            Output(self.store.boxplot_nplayers, 'data'),
            Input(self.store.currentsplit, 'data'),
        )
        def set_boxplot_title_data(split: str) -> Tuple[int, int]:
            clusterid = 100
            nplayers = 1234
            return clusterid, nplayers

        @self.app.callback(
            Output(self.view, 'children'),
            *[Input(getattr(self.store, field.name), 'data')
              for field in fields(self.store)],
        )
        def update_view(*storevals):
            contents = []
            for field, val in zip(fields(self.store), storevals):
                contents.append(f"{field.name}: {val}")
            return ', '.join(contents)
