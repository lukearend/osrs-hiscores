from typing import List, Tuple, OrderedDict

from dash import Dash, Input, Output

from src.data.types import SplitResults


def add_boxplot(app: Dash, app_data: OrderedDict[str, SplitResults]) -> Dash:

    @app.callback(
        Output('boxplot:tickskills', 'data'),
        Input('controls:split', 'data'),
    )
    def update_boxplot_split(newsplit: str) -> List[str]:
        return app_data[newsplit].skills

    @app.callback(
        Output('boxplot:title:clusterid', 'data'),
        Output('boxplot:title:nplayers', 'data'),
        Input('controls:split', 'data'),
    )
    def update_boxplot_title(newsplit) -> Tuple[int, int]:
        clusterid = 100
        nplayers = app_data[newsplit].cluster_sizes
        return clusterid, nplayers

    return app
