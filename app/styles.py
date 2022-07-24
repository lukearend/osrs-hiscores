""" Visual styling constants. """

import plotly.express as px

bg_gray = '#222222'
dark_gray = '#111111'
error_red = '#dc3545'
success_green = '#198754'
table_gray = '#444444'
white = '#ffffff'

BG_COLOR = bg_gray
MENU_VARIANT = 'dark'
PLAYER_COLOR_SEQ = px.colors.qualitative.Plotly

SCATTERPLOT_HEIGHT = '28em'
SCATTERPLOT_BG_COLOR = dark_gray
SCATTERPLOT_XAXIS_COLOR = '#222222'
SCATTERPLOT_YAXIS_COLOR = '#262626'
SCATTERPLOT_ZAXIS_COLOR = '#303030'
SCATTERPLOT_PTS_OPACITY = 0.5
SCATTERPLOT_PTSIZE_CONSTANT = 0.25
SCATTERPLOT_MAX_PTSIZE = 25
SCATTERPLOT_HALO_SIZE = 75
SCATTERPLOT_HALO_NSHADES = 25
SCATTERPLOT_TEXT_FONT_SIZE = 24

TABLE_BG_COLOR = dark_gray
TABLE_BORDER_COLOR = table_gray

BOXPLOT_HEIGHT = '10em'
BOXPLOT_AXIS_FONTSIZE = 20
BOXPLOT_BG_COLOR = dark_gray
BOXPLOT_PAPER_COLOR = BG_COLOR

DROPDOWN_LABEL_WIDTHS = dict(xs=12, lg='auto')
DROPDOWN_WIDTHS = dict(xs=4, lg='auto')
INPUTBOX_LAYOUT = dict(sm=True)
LOOKUP_SECTION_LAYOUT = dict(xs=dict(order=1, size=12), lg=dict(order=1, size=5))
TABLE_SECTION_LAYOUT = dict(xs=dict(order=2, size=12), lg=dict(order=2, size=5))
SCATTER_SECTION_LAYOUT = dict(xs=dict(order=3, size=12), lg=dict(order=4, size=7))
FLOATING_BREAK1_LAYOUT = dict(xs=dict(order=4, size=12), lg=dict(order=5, size=7))
BOXPLOT_SECTION_LAYOUT = dict(xs=dict(order=4, size=12), lg=dict(order=3, size=5))
FLOATING_BREAK2_LAYOUT = dict(xs=dict(order=5, size=12), lg=dict(order=4, size=7))
WATERMARK_SECTION_LAYOUT = dict(xs=dict(order=5, size=12), lg=dict(order=4, size=7))
