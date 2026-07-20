"""Typed view over an incoming platform request.

The platform posts the same envelope to every handler: a top-level ``data``
object and a top-level ``credentials`` envelope. What ``data`` contains depends
on the endpoint:

* ``/execute`` — ``data`` *is* the user's input properties.
* ``/schema`` and ``/content`` — ``data`` carries ``form_data`` (the current
  field values) and, for content, ``content_object_names``.

``Request`` exposes each of these as a typed accessor so handlers read
``request.data`` / ``request.form_data`` / ``request.content_object_names`` /
``request.credentials`` without digging through nested dicts.
"""

from __future__ import annotations

from typing import Any

from stacksync_cdk.credentials import Credentials


class Request:
    """Parsed, read-only view of a connector request body."""

    def __init__(self, payload: dict[str, Any] | None):
        self._payload: dict[str, Any] = payload or {}

    @property
    def json(self) -> dict[str, Any]:
        """The full request body."""
        return self._payload

    @property
    def data(self) -> dict[str, Any]:
        """The top-level ``data`` object.

        For ``/execute`` this is the user's input properties. For ``/schema``
        and ``/content`` it is the context object holding ``form_data`` etc.
        """
        data = self._payload.get("data")
        return data if isinstance(data, dict) else {}

    @property
    def form_data(self) -> dict[str, Any]:
        """The current field values (``data.form_data``) for schema/content."""
        form_data = self.data.get("form_data")
        return form_data if isinstance(form_data, dict) else {}

    @property
    def content_object_names(self) -> list[str]:
        """The requested content-object ids (``data.content_object_names``).

        Normalizes entries that arrive as ``{"id": ...}`` dicts down to their
        string ids.
        """
        raw = self.data.get("content_object_names") or []
        names: list[str] = []
        for entry in raw:
            if isinstance(entry, dict):
                name = entry.get("id") or entry.get("content_object_name") or entry.get("name")
                if name:
                    names.append(name)
            elif isinstance(entry, str):
                names.append(entry)
        return names

    @property
    def credentials(self) -> Credentials:
        """The connection's credentials, typed and unwrapped."""
        return Credentials.from_payload(self._payload)
