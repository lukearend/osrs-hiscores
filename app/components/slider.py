""" Range slider for selecting a level range. """

import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import Input, Output, html

from app import app
from app.components.space import vspace


def level_range_slider():

    slider = dcc.RangeSlider(
        id='level-range-slider',
        step=1,
        allowCross=False,
        tooltip=dict(
            placement='bottom'
        ),
    )
    label = html.Strong(
        "Show levels:",
        className='controls-text',
    )
    return dbc.Row(
        [
            dbc.Col(label, width='auto'),
            dbc.Col([
                vspace(),  # vertically aligns slider bar with label text
                slider,
            ]),
        ],
        align='center',
        className='g-0',
    )

@app.callback(
    Output('level-range-slider', 'min'),
    Output('level-range-slider', 'max'),
    Output('level-range-slider', 'value'),
    Output('level-range-slider', 'marks'),
    Input('color-by-skill', 'data'),
)
def update_range(skill: str) -> dbc.Col:
    if skill == 'total':
        ticks = [500, 750, 1000, 1250, 1500, 1750, 2000, 2277]
    else:
        ticks = [1, 20, 40, 60, 80, 99]
    range = min(ticks), max(ticks)
    marks = {n: str(n) for n in ticks}
    return range[0], range[1], range, marks
