from typing import Dict, Any

import dash_core_components as dcc
from plotly import graph_objects as go
from dash import Output, Input, no_update

from app import app


@app.callback(
    Output('scatterplot', 'extendData'),
    Input('scatterplot-data', 'data'),
)
def update_scatterplot_traces(data_dict: Dict[str, Any]):
    if not data_dict:
        return no_update

    traces = {
        'x': data_dict['x'],
        'y': data_dict['y'],
        'z': data_dict['z'],
    }

    extendtraces = {name: [data] for name, data in traces.items()}
    extendinds = [0]
    maxpts = len(traces['x'])
    return [extendtraces, extendinds, maxpts]


def scatterplot():
    clustertrace = go.Scatter3d(
        x=[1, 2, 3, 4, 5],
        y=[1, 2, 3, 2, 1],
        z=[5, 1, 2, 3, 4],
    )

    fig = go.Figure(data=clustertrace)

    return dcc.Graph(
        id='scatterplot',
        figure=fig,
        className='scatterplot-graph',
    )
