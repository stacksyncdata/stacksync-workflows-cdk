"""Input coercion helpers for connector handlers.

These mirror the helpers connectors relied on in the previous CDK so that
values arriving as JSON strings (a common shape from form widgets) can be
parsed into real Python objects without each connector re-implementing it.
"""

from __future__ import annotations

import json
from typing import Any


def parse_str_to_json(data: str) -> Any:
    """Parse a JSON string, raising ``ValueError`` on malformed input."""
    try:
        return json.loads(data)
    except json.JSONDecodeError as error:
        raise ValueError("Invalid JSON string") from error


def validate_and_parse_json(data: Any, field_name: str) -> Any:
    """Return ``data`` as a parsed object; parse it first if it is a JSON string."""
    if isinstance(data, str):
        return parse_str_to_json(data)
    if isinstance(data, (dict, list)):
        return data
    raise ValueError(f"{field_name} must be a JSON string, dictionary, or list")


def validate_array(data: Any, field_name: str) -> list[Any]:
    """Return ``data`` as a list, parsing a JSON-string array if needed."""
    if isinstance(data, str):
        parsed = parse_str_to_json(data)
        if not isinstance(parsed, list):
            raise ValueError(f"{field_name} must be an array")
        return parsed
    if isinstance(data, list):
        return data
    raise ValueError(f"{field_name} must be an array")


def validate_object(data: Any, field_name: str) -> dict[str, Any]:
    """Return ``data`` as a dict, parsing a JSON-string object if needed."""
    if isinstance(data, str):
        parsed = parse_str_to_json(data)
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name} must be an object")
        return parsed
    if isinstance(data, dict):
        return data
    raise ValueError(f"{field_name} must be an object")
