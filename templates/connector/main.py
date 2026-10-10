"""Entry point for the connector.

The CDK's app factory discovers the modules under ``modules/`` and wires up the
routes. The Stacksync CLI boots ``app`` for local runs, and Stacksync serves the
same ``app`` once the connector is deployed.
"""

import os

from stacksync_cdk import create_app

app = create_app(os.path.dirname(os.path.abspath(__file__)))
