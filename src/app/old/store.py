from typing import List, OrderedDict, Tuple

import dash_core_components as dcc
from dash import Dash, Input, Output, html

from src.data.types import SplitResults


def build_store(app: Dash, app_data: OrderedDict[str, SplitResults]) -> html.Div:
    store = [
        split := dcc.Store(id='controls:split'),
        bpticks := dcc.Store(id='boxplot:tickskills'),
        bpcluster := dcc.Store(id='boxplot:clusterid'),
        bpnplayers := dcc.Store(id='boxplot:nplayers'),
    ]

    # Debugging: viewer
    store.append(viewer := html.Div(children=None))
    @app.callback(
        Output(viewer, 'children'),
        Input(split, 'data'),
        Input(bpticks, 'data'),
        Input(bpcluster, 'data'),
        Input(bpnplayers, 'data'),
    )
    def update_store_view(split, tickskills, clusterid, nplayers) -> html.Div:
        return html.Div([
            f"controls:split {split}",
            f"boxplot:clusterid {clusterid}",
            f"boxplot:nplayers {nplayers}",
            f"boxplot:tickskills {tickskills}",
        ])

    return html.Div(store)
