import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import html

from app.components.space import vspace


def total_lvl_slider():
    ticks = [500, 750, 1000, 1250, 1500, 1750, 2000, 2277]
    slider = dcc.RangeSlider(
        id='total-lvl-slider',
        step=1,
        min=500,
        max=2277,
        value=[500, 2277],
        marks={n: str(n) for n in ticks},
        allowCross=False,
        tooltip=dict(placement='bottom'),
    )
    label = html.Strong(
        "Show total levels:",
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
    )
