"""The standard every connector must meet before Stacksync deploys it.

The checks only read files: they never import or run the connector's code, so the
deployment service can run them on an untrusted upload. The same rules run in three
places, so a connector learns about a problem as early as possible:

  - ``create_app`` logs each problem as a warning when the connector starts.
  - ``python -m stacksync_cdk.connector_checks [<connector folder>]`` lists them and
    exits with status 1 (AI coding assistants run this before they finish).
  - The Stacksync deployment service rejects a submission that has any of them.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Any

import yaml

GENERIC_CONNECTION_APP_TYPE = "generic_api_credentials"
# Connections holding a Stacksync API key, for connectors whose modules call Stacksync's public API
STACKSYNC_API_KEY_CONNECTION_APP_TYPES = ("stacksync_user_api_key", "stacksync_workspace_api_key")

REQUIRED_APP_SETTINGS = (
    "app_type",
    "app_name",
    "app_type_display",
    "app_description",
    "app_icon_svg_url",
    "connection_app_type",
)

# Values the template ships with; leaving one in place means the setting was never filled.
TEMPLATE_PLACEHOLDER_VALUES = frozenset(
    {
        "YOUR_WORKSPACE_ID_HERE",
        "my_app",
        "My App",
        "A concise description of your app and its capabilities.",
    }
)

# Everything else at the connector root is rejected, so workflow code, scripts and
# notes never ship inside a connector. Hidden entries (.venv, .git, ...) are left to
# the CLI, which never uploads them; Dockerfile and gunicorn_config.py are replaced
# by Stacksync's own at build time.
ALLOWED_ROOT_ENTRIES = frozenset(
    {
        "main.py",
        "stacksync.yml",
        "requirements.txt",
        "context.md",
        "README.md",
        "LICENSE",
        "AGENTS.md",
        "CLAUDE.md",
        "Dockerfile",
        "gunicorn_config.py",
        "modules",
        "utils",
        "tests",
        "guide",
        "__pycache__",
        # Python project files a connector may keep for its own tooling and tests.
        "pyproject.toml",
        "uv.lock",
        "requirements-dev.txt",
        "conftest.py",
        "pytest.ini",
    }
)

APP_CONTEXT_SECTIONS = ("What this app is", "Connection", "Objects", "App-wide limits")
MODULE_CONTEXT_SECTIONS = ("What it does", "Connection", "Inputs", "Output", "Limits & errors")

EXAMPLES_START_MARKER = "## EXAMPLES start ##"
EXAMPLES_END_MARKER = "## EXAMPLES end ##"

# The text `stacksync workflow-connector module create` writes into a new context.md.
CONTEXT_STUB_TEXT = "Describe what this module does"

# "## Inputs" and "## Inputs ##" are the same heading.
_HEADING = re.compile(r"^##\s+(.+?)[\s#]*$", re.MULTILINE)
# A placeholder is a line that starts with TODO; the word inside content ("status: TODO or DONE") is fine.
_TODO_LINE = re.compile(r"^\s*(?:[-*]\s*)?TODO\b", re.MULTILINE)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_VERSION_DIRECTORY = re.compile(r"^v\d\w*$")


@dataclass(frozen=True)
class ConnectorProblem:
    """One way the connector misses the standard. ``path`` is relative to the connector root."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def find_connector_problems(root: str) -> list[ConnectorProblem]:
    """
    Check a connector folder against the standard, reading files only.

    :param root: the connector folder (the one that holds stacksync.yml)
    :return: every problem found, in a stable order; empty when the connector meets the standard
    """
    problems = _find_app_settings_problems(root)
    problems += _find_root_entry_problems(root)
    problems += _find_context_problems(
        root, "context.md", APP_CONTEXT_SECTIONS, needs_examples=False
    )
    for version_path in _list_module_version_paths(root):
        problems += _find_context_problems(
            root, f"{version_path}/context.md", MODULE_CONTEXT_SECTIONS, needs_examples=True
        )
    return problems


def _find_app_settings_problems(root: str) -> list[ConnectorProblem]:
    manifest_path = os.path.join(root, "stacksync.yml")
    if not os.path.isfile(manifest_path):
        return [ConnectorProblem("stacksync.yml", "the file is missing")]
    try:
        with open(manifest_path, encoding="utf-8") as manifest_file:
            manifest = yaml.safe_load(manifest_file) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return [ConnectorProblem("stacksync.yml", "the file is not valid YAML")]
    app_settings = manifest.get("app_settings") if isinstance(manifest, dict) else None
    if not isinstance(app_settings, dict):
        return [ConnectorProblem("stacksync.yml", "app_settings is missing")]

    problems: list[ConnectorProblem] = []
    for setting_name in REQUIRED_APP_SETTINGS:
        value = _read_text_setting(app_settings, setting_name)
        if not value:
            problems.append(
                ConnectorProblem("stacksync.yml", f"app_settings.{setting_name} is required")
            )
        elif value in TEMPLATE_PLACEHOLDER_VALUES:
            problems.append(
                ConnectorProblem(
                    "stacksync.yml", f"app_settings.{setting_name} still has the template value"
                )
            )

    icon_url = _read_text_setting(app_settings, "app_icon_svg_url")
    if icon_url and not icon_url.startswith("https://"):
        problems.append(
            ConnectorProblem(
                "stacksync.yml", "app_settings.app_icon_svg_url must start with https://"
            )
        )

    app_type = _read_text_setting(app_settings, "app_type")
    connection_app_type = _read_text_setting(app_settings, "connection_app_type")
    shared_connection_app_types = (
        GENERIC_CONNECTION_APP_TYPE,
        *STACKSYNC_API_KEY_CONNECTION_APP_TYPES,
    )
    if connection_app_type and connection_app_type not in (*shared_connection_app_types, app_type):
        problems.append(
            ConnectorProblem(
                "stacksync.yml",
                "app_settings.connection_app_type must be one of "
                f"{', '.join(shared_connection_app_types)} "
                f"or the app's own app_type ({app_type})",
            )
        )
    return problems


def _read_text_setting(app_settings: dict[str, Any], setting_name: str) -> str:
    value = app_settings.get(setting_name)
    return str(value).strip() if value is not None else ""


def _find_root_entry_problems(root: str) -> list[ConnectorProblem]:
    return [
        ConnectorProblem(
            entry_name, "is not part of a connector; move it out of the connector folder"
        )
        for entry_name in sorted(os.listdir(root))
        if not entry_name.startswith(".") and entry_name not in ALLOWED_ROOT_ENTRIES
    ]


def _list_module_version_paths(root: str) -> list[str]:
    """The ``modules/<module>/v<N>`` paths ``create_app`` serves, relative to the root."""
    modules_path = os.path.join(root, "modules")
    if not os.path.isdir(modules_path):
        return []
    version_paths = []
    for module_name in sorted(os.listdir(modules_path)):
        module_path = os.path.join(modules_path, module_name)
        if not os.path.isdir(module_path) or module_name.startswith((".", "_")):
            continue
        for version_name in sorted(os.listdir(module_path)):
            if os.path.isdir(os.path.join(module_path, version_name)) and _VERSION_DIRECTORY.match(
                version_name
            ):
                version_paths.append(f"modules/{module_name}/{version_name}")
    return version_paths


def _find_context_problems(
    root: str, context_path: str, required_sections: tuple[str, ...], *, needs_examples: bool
) -> list[ConnectorProblem]:
    try:
        with open(os.path.join(root, context_path), encoding="utf-8") as context_file:
            context = context_file.read()
    except FileNotFoundError:
        return [ConnectorProblem(context_path, "the file is missing")]
    except (OSError, UnicodeDecodeError):
        return [ConnectorProblem(context_path, "the file is not readable UTF-8 text")]

    if CONTEXT_STUB_TEXT in context:
        return [ConnectorProblem(context_path, "still has the placeholder text; write the context")]

    visible_text = _HTML_COMMENT.sub("", context)
    problems: list[ConnectorProblem] = []
    if _TODO_LINE.search(visible_text):
        problems.append(ConnectorProblem(context_path, "still has TODO items; fill them in"))

    sections = _split_sections(visible_text)
    for section_name in required_sections:
        section_text = sections.get(section_name.lower())
        if section_text is None:
            problems.append(
                ConnectorProblem(context_path, f'the "## {section_name}" section is missing')
            )
        elif not section_text.strip():
            problems.append(
                ConnectorProblem(context_path, f'the "## {section_name}" section is empty')
            )

    if needs_examples and not _has_examples(visible_text):
        problems.append(
            ConnectorProblem(
                context_path,
                f'needs at least one example between "{EXAMPLES_START_MARKER}" and "{EXAMPLES_END_MARKER}"',
            )
        )
    return problems


def _split_sections(context: str) -> dict[str, str]:
    """Each ``## heading`` (lower-cased) mapped to the text up to the next one."""
    headings = list(_HEADING.finditer(context))
    sections = {}
    for index, heading in enumerate(headings):
        section_end = headings[index + 1].start() if index + 1 < len(headings) else len(context)
        sections.setdefault(heading.group(1).lower(), context[heading.end() : section_end])
    return sections


def _has_examples(context: str) -> bool:
    start = context.find(EXAMPLES_START_MARKER)
    end = context.find(EXAMPLES_END_MARKER)
    if start == -1 or end <= start:
        return False
    return "FORM DATA:" in context[start:end]


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    problems = find_connector_problems(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} problem(s) to fix before this connector can be deployed.")
        return 1
    print("The connector meets the Stacksync standard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
