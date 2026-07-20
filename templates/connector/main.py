"""Entry point for the connector.

The CDK's app factory discovers the modules under ``modules/`` and wires up the
routes. Serve this with ``gunicorn main:app`` (see ``gunicorn_config.py``); the
Stacksync CLI boots the same ``app`` for local runs.
"""

import os

from stacksync_cdk import create_app

app = create_app(os.path.dirname(os.path.abspath(__file__)))
