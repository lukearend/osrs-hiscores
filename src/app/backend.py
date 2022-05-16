from typing import OrderedDict, Tuple

from dash import Dash, Output, Input

from src.app.store import BackendState, FrontendState
from src.data.types import SplitResults


class Backend:
    """ Behind-the-scenes queries and data manipulation. """

    def __init__(self, app: Dash, app_data: OrderedDict[str, SplitResults], frontend: FrontendState):
        self.app = app
        self.app_data = app_data
        self.frontend = frontend
        self.state = BackendState(
            currentsplit=None,
        )

    def add_callbacks(self):

        @self.app.callback(
            Output(self.state.currentsplit, 'data'),
            Input(self.frontend.splitmenu.split, 'data'),
        )
        def set_current_split(split: str) -> str:
            return split

        @self.app.callback(
            Output(self.frontend.boxplot.clusterid, 'data'),
            Output(self.frontend.boxplot.nplayers, 'data'),
            Input(self.state.currentsplit, 'data'),
        )
        def set_boxplot_title_data(split: str) -> Tuple[int, int]:
            clusterid = 100
            nplayers = 1234
            return clusterid, nplayers
