from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import pytest

from stacksync_cdk import create_app
from stacksync_cdk.connector_checks import find_connector_problems

_STACKSYNC_YML = """\
deployment_settings:
  workspace: "4337"
  region: usnv
app_settings:
  app_type: acme_crm
  app_name: ACME CRM
  app_type_display: ACME CRM
  app_icon_svg_url: https://cdn.acme.example/logo.svg
  app_description: Create and read ACME CRM records.
  connection_app_type: generic_api_credentials
"""

_APP_CONTEXT = """\
# ACME CRM

## What this app is
Connects to ACME CRM through its REST API at https://api.acme.example.

## Connection
A generic_api_credentials connection; `api_credentials` holds the bearer token.

## Objects
Standard objects (contact, deal) and custom objects, listed live from GET /objects.

## App-wide limits
100 requests per minute; a 429 carries Retry-After.
"""

_MODULE_CONTEXT = """\
# Create Records

## What it does
Creates records of the chosen object and returns them.

## Connection
The app's generic_api_credentials connection.

## Inputs
- `select_object` (required) -> the object; options come from /content.

## Output
`data` is the list of created records.

## Limits & errors
At most 100 records per run -> "Maximum 100 records per request".

## EXAMPLES start ##
### Create one contact
FORM DATA:
{"summary": "Create one contact", "changes": []}
## EXAMPLES end ##
"""

_SCHEMA_WITHOUT_CONNECTIONS = """\
from stacksync_cdk import Request, SchemaResponse


def schema(request: Request) -> SchemaResponse:
    return SchemaResponse([{"id": "select_object", "type": "string", "label": "Select object"}])
"""


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")


@pytest.fixture
def complete_connector(tmp_path: Path) -> Path:
    """A connector that meets the standard, with one module (create_records/v1)."""
    _write(tmp_path / "stacksync.yml", _STACKSYNC_YML)
    _write(tmp_path / "context.md", _APP_CONTEXT)
    _write(tmp_path / "main.py", "")
    module = tmp_path / "modules" / "create_records" / "v1"
    _write(module / "context.md", _MODULE_CONTEXT)
    _write(module / "schema.py", _SCHEMA_WITHOUT_CONNECTIONS)
    return tmp_path


def _messages(root: Path) -> list[str]:
    return [str(problem) for problem in find_connector_problems(str(root))]


def test_complete_connector_has_no_problems(complete_connector):
    assert _messages(complete_connector) == []


@pytest.mark.parametrize(
    "connection_app_type", ["stacksync_user_api_key", "stacksync_workspace_api_key"]
)
def test_a_connector_may_use_a_stacksync_api_key_connection(
    complete_connector, connection_app_type
):
    manifest = complete_connector / "stacksync.yml"
    manifest.write_text(
        manifest.read_text().replace(
            "  connection_app_type: generic_api_credentials",
            f"  connection_app_type: {connection_app_type}",
        )
    )
    assert _messages(complete_connector) == []


def test_hidden_entries_and_build_files_are_ignored(complete_connector):
    for name in (".venv", ".stacksync_build", ".logs"):
        (complete_connector / name).mkdir()
    _write(complete_connector / "Dockerfile", "FROM scratch\n")
    assert _messages(complete_connector) == []


@pytest.mark.parametrize(
    ("old_line", "new_line", "expected"),
    [
        (
            "  app_icon_svg_url: https://cdn.acme.example/logo.svg",
            '  app_icon_svg_url: ""',
            "stacksync.yml: app_settings.app_icon_svg_url is required",
        ),
        (
            "  app_icon_svg_url: https://cdn.acme.example/logo.svg",
            "  app_icon_svg_url: http://cdn.acme.example/logo.svg",
            "stacksync.yml: app_settings.app_icon_svg_url must start with https://",
        ),
        (
            "  connection_app_type: generic_api_credentials\n",
            "",
            "stacksync.yml: app_settings.connection_app_type is required",
        ),
        (
            "  connection_app_type: generic_api_credentials",
            "  connection_app_type: salesforce",
            "stacksync.yml: app_settings.connection_app_type must be one of "
            "generic_api_credentials, stacksync_user_api_key, stacksync_workspace_api_key "
            "or the app's own app_type (acme_crm)",
        ),
        (
            "  app_name: ACME CRM",
            "  app_name: My App",
            "stacksync.yml: app_settings.app_name still has the template value",
        ),
    ],
)
def test_app_settings_problems(complete_connector, old_line, new_line, expected):
    manifest = complete_connector / "stacksync.yml"
    manifest.write_text(manifest.read_text().replace(old_line, new_line))
    assert _messages(complete_connector) == [expected]


def test_own_app_type_is_an_accepted_connection(complete_connector):
    manifest = complete_connector / "stacksync.yml"
    manifest.write_text(manifest.read_text().replace("generic_api_credentials", "acme_crm"))
    assert _messages(complete_connector) == []


def test_missing_manifest(complete_connector):
    (complete_connector / "stacksync.yml").unlink()
    assert _messages(complete_connector) == ["stacksync.yml: the file is missing"]


def test_unknown_root_entries_are_rejected(complete_connector):
    _write(complete_connector / "flows" / "f1" / "test_mapping.py", "print('hi')\n")
    _write(complete_connector / "notes.txt", "todo\n")
    assert _messages(complete_connector) == [
        "flows: is not part of a connector; move it out of the connector folder",
        "notes.txt: is not part of a connector; move it out of the connector folder",
    ]


def test_missing_contexts(complete_connector):
    (complete_connector / "context.md").unlink()
    (complete_connector / "modules" / "create_records" / "v1" / "context.md").unlink()
    assert _messages(complete_connector) == [
        "context.md: the file is missing",
        "modules/create_records/v1/context.md: the file is missing",
    ]


def test_cli_stub_context_is_rejected(complete_connector):
    _write(
        complete_connector / "modules" / "create_records" / "v1" / "context.md",
        "# Create Records\n\nDescribe what this module does, its inputs, and its outputs.\n",
    )
    assert _messages(complete_connector) == [
        "modules/create_records/v1/context.md: still has the placeholder text; write the context"
    ]


def test_module_context_section_problems(complete_connector):
    context_path = complete_connector / "modules" / "create_records" / "v1" / "context.md"
    context = context_path.read_text()
    context = context.replace("## Output\n`data` is the list of created records.\n", "")
    context = context.replace(
        "The app's generic_api_credentials connection.",
        "<!-- which connection, and the keys read -->",
    )
    context = context.replace("At most 100 records per run", "TODO: the API's real limit")
    context_path.write_text(context)
    assert _messages(complete_connector) == [
        "modules/create_records/v1/context.md: still has TODO items; fill them in",
        'modules/create_records/v1/context.md: the "## Connection" section is empty',
        'modules/create_records/v1/context.md: the "## Output" section is missing',
    ]


def test_module_context_needs_an_example(complete_connector):
    context_path = complete_connector / "modules" / "create_records" / "v1" / "context.md"
    context = context_path.read_text()
    context_path.write_text(context[: context.index("## EXAMPLES start ##")])
    assert _messages(complete_connector) == [
        'modules/create_records/v1/context.md: needs at least one example between "## EXAMPLES start ##" '
        'and "## EXAMPLES end ##"'
    ]


def test_app_context_needs_objects_and_connection(complete_connector):
    _write(
        complete_connector / "context.md",
        "# ACME CRM\n\n## What this app is\nA CRM.\n\n## App-wide limits\nNone.\n",
    )
    assert _messages(complete_connector) == [
        'context.md: the "## Connection" section is missing',
        'context.md: the "## Objects" section is missing',
    ]


def test_schema_gets_the_declared_connection(complete_connector):
    client = create_app(str(complete_connector)).test_client()
    schema = client.post("/create_records/v1/schema", json={}).get_json()["data"]["schema"]
    assert schema["connections"] == {
        "required": True,
        "app_types": ["generic_api_credentials"],
        "allowed_connection_management_types": ["managed"],
    }


def test_schema_keeps_a_connection_the_handler_sets(connector_root):
    manifest = connector_root / "stacksync.yml"
    manifest.write_text(manifest.read_text() + "  connection_app_type: acme\n")
    client = create_app(str(connector_root)).test_client()
    schema = client.post("/create_records/v1/schema", json={}).get_json()["data"]["schema"]
    assert schema["connections"]["app_types"] == ["generic_api_credentials"]


def test_app_config_exposes_the_connection_app_type(complete_connector):
    client = create_app(str(complete_connector)).test_client()
    app_settings = client.get("/app-config").get_json()["data"]["app_settings"]
    assert app_settings["connection_app_type"] == "generic_api_credentials"


def test_problems_are_logged_at_start_but_the_app_still_serves(complete_connector, caplog):
    (complete_connector / "context.md").unlink()
    with caplog.at_level(logging.WARNING):
        client = create_app(str(complete_connector)).test_client()
    assert "Must fix before deploying: context.md: the file is missing" in caplog.text
    assert client.get("/health").status_code == 200


def test_start_is_refused_without_an_app_type(complete_connector):
    manifest = complete_connector / "stacksync.yml"
    manifest.write_text(manifest.read_text().replace("  app_type: acme_crm\n", ""))
    with pytest.raises(ValueError, match="app_settings.app_type is required"):
        create_app(str(complete_connector))


def test_todo_as_content_and_closing_hashes_are_accepted(complete_connector):
    context_path = complete_connector / "modules" / "create_records" / "v1" / "context.md"
    context = context_path.read_text()
    context = context.replace("## Inputs\n", "## Inputs ##\n")
    context = context.replace(
        "(required) -> the object;", "(required) -> the object, e.g. a task in TODO status;"
    )
    context_path.write_text(context)
    assert _messages(complete_connector) == []


def test_python_project_files_are_accepted_at_the_root(complete_connector):
    for file_name in (
        "pyproject.toml",
        "uv.lock",
        "requirements-dev.txt",
        "conftest.py",
        "pytest.ini",
    ):
        _write(complete_connector / file_name, "\n")
    assert _messages(complete_connector) == []
