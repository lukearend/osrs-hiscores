from typing import Dict, Any

import dash_core_components as dcc
from plotly import graph_objects as go
from dash import State, Output, Input, no_update

from app import app


@app.callback(
    Output('scatterplot', 'extendData'),
    Input('scatterplot-data', 'data'),
)
def update_scatterplot_traces(data_dict: Dict[str, Any]):
    if not data_dict:
        return no_update

    traces = {
        'x': data_dict['cluster_x'],
        'y': data_dict['cluster_y'],
        'z': data_dict['cluster_z'],
    }

    extendtraces = {name: [data] for name, data in traces.items()}
    extendinds = [0]
    maxpts = len(traces['x'])
    return [extendtraces, extendinds, maxpts]


@app.callback(
    Output('scatterplot', 'figure'),
    Input('current-split', 'data'),
    State('scatterplot-data', 'data'),
)
def redraw_scatterplot(split: str, data_dict: Dict[str, Any]) -> go.Figure:
    if split is None:
        return no_update
    if not data_dict:
        return no_update

    clustertrace = go.Scatter3d(
        x=data_dict['cluster_x'],
        y=data_dict['cluster_y'],
        z=data_dict['cluster_z'],
    )

    fig = go.Figure(data=clustertrace)

    return fig


def scatterplot():
    return dcc.Graph(
        id='scatterplot',
        figure={},
        className='scatterplot-graph',
    )
