"""Stacksync Connector Development Kit — build connectors for Stacksync Workflows.

A connector's handlers parse a typed :class:`Request` and return a typed response
(:class:`SchemaResponse`, :class:`ContentResponse`, :class:`ExecuteResponse`).
:func:`create_app` discovers the modules on disk and serves them in the format the
platform expects, so you write only your logic.
"""

from stacksync_cdk.app import create_app
from stacksync_cdk.credentials import Credentials
from stacksync_cdk.errors import ManagedError
from stacksync_cdk.module_config import ModuleConfig
from stacksync_cdk.request import Request
from stacksync_cdk.responses import (
    ContentResponse,
    ExecuteResponse,
    Response,
    SchemaResponse,
)
from stacksync_cdk.validation import (
    parse_str_to_json,
    validate_and_parse_json,
    validate_array,
    validate_object,
)

__all__ = [
    "create_app",
    "Request",
    "Credentials",
    "Response",
    "SchemaResponse",
    "ContentResponse",
    "ExecuteResponse",
    "ManagedError",
    "ModuleConfig",
    "validate_and_parse_json",
    "validate_array",
    "validate_object",
    "parse_str_to_json",
]
