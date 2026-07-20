"""Shared fixtures: a throwaway connector on disk, served by ``create_app``."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from stacksync_cdk import create_app

_STACKSYNC_YML = """\
app_settings:
  app_type: acme
  app_name: ACME CRM
  app_type_display: ACME CRM
  app_description: A test connector.
"""

_SCHEMA_PY = """\
from stacksync_cdk import Request, SchemaResponse

CONNECTIONS = {
    "required": True,
    "app_types": ["generic_api_credentials"],
    "allowed_connection_management_types": ["managed"],
}


def schema(request: Request) -> SchemaResponse:
    fields = [
        {"id": "record_type", "type": "string", "label": "Record type",
         "on_action": {"load_schema": True},
         "content": {"content_objects": [{"id": "record_type"}]}},
    ]
    if request.credentials and request.form_data.get("record_type"):
        fields.append({"id": "status", "type": "string", "label": "Status"})
    return SchemaResponse(fields, connections=CONNECTIONS)
"""

_CONTENT_PY = """\
from stacksync_cdk import ContentResponse, Request


def content(request: Request) -> ContentResponse:
    content_objects = {}
    for name in request.content_object_names:
        if name == "record_type":
            content_objects["record_type"] = [
                {"value": "contact", "label": "Contact"},
                {"value": "deal", "label": "Deal"},
            ]
    return ContentResponse(content_objects)
"""

_EXECUTE_PY = """\
from stacksync_cdk import ExecuteResponse, ManagedError, Request


def execute(request: Request) -> ExecuteResponse:
    if not request.credentials:
        raise ManagedError.unauthorized("No credentials provided")
    record_type = request.data.get("record_type")
    if record_type == "boom":
        raise RuntimeError("unexpected failure")
    return ExecuteResponse(
        {"created": record_type, "api_key_seen": request.credentials.api_key},
        metadata={"affected_records": 1},
        data_type="record",
    )
"""

_CONFIG_PY = """\
from stacksync_cdk import ModuleConfig

CONFIG = ModuleConfig(
    module_name="Create Records",
    module_description="Create an ACME CRM record.",
    requires_credentials_for_schema=False,
)
"""


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")


@pytest.fixture
def connector_root(tmp_path: Path) -> Path:
    """A minimal connector with one module (``create_records/v1``) on disk."""
    _write(tmp_path / "stacksync.yml", _STACKSYNC_YML)
    module = tmp_path / "modules" / "create_records" / "v1"
    _write(module / "schema.py", _SCHEMA_PY)
    _write(module / "content.py", _CONTENT_PY)
    _write(module / "execute.py", _EXECUTE_PY)
    _write(module / "config.py", _CONFIG_PY)
    return tmp_path


@pytest.fixture
def client(connector_root: Path):
    app = create_app(str(connector_root))
    app.testing = True
    return app.test_client()


def credentials_envelope(value: dict | None = None) -> dict:
    return {
        "connection_data": {
            "value": value if value is not None else {"api_key": "secret-123"},
            "connection_app_type": "generic_api_credentials",
            "connection_id": "conn-1",
        },
        "connection_management_type": "managed",
    }
