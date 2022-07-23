#!/usr/bin/env python3

""" Entry point for main application. """

import os
from app import app
from app.helpers import index_html
from app.root import root_layout

app.title = "OSRS hiscores explorer"
app.layout = root_layout()
app.index_string = index_html()

server = app.server  # used by gunicorn
if not os.getenv('ON_HEROKU'):
    app.run_server(
        host='0.0.0.0' if os.getenv('ON_HEROKU') else 'localhost',
        debug=True if os.getenv('OSRS_DEBUG') else False,
        port=os.getenv('PORT', 8050)
    )
