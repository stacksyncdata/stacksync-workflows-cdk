"""Typed access to a connection's credentials.

The platform delivers credentials wrapped in a fixed envelope::

    {
      "connection_data": {
        "value": { ...the secret payload... },
        "connection_app_type": "hubspot",
        "connection_id": "...",
        "rate_limiter": { ... }
      },
      "connection_management_type": "managed"
    }

``value`` is a **flat dict**, one level under ``connection_data``. There is no
deeper nesting to dig through; read your keys straight off it. **Which keys are
in it is defined entirely by the connection type your module declares in
``app_types`` — not by your app.** Read the exact key names that connection type
stores. The common shapes:

* ``generic_api_credentials`` — has exactly ONE field, ``api_credentials``, a
  free-form string (an API key, a token, a connection string, or a pasted JSON
  blob). It does NOT give you named fields::

      {"api_credentials": "sk-...."}          # a key/token
      {"api_credentials": "{\"url\": ...}"}   # or a JSON string YOU must json.loads

  So ``.get("url")`` is ``None`` here — the only key is ``api_credentials``. If
  you need structured multi-field credentials (an instance URL + database +
  user + key, say), do NOT use ``generic_api_credentials``: use a dedicated
  connection type (below).

* A **dedicated type** (one Stacksync sets up for your app) — ``value`` is the
  exact fields that type's form collects, so read those exact names. Field names
  are whatever that type defines (they vary per app), e.g.::

      {"api_key": "k-123", "instance_url": "https://acme.example.com"}

* **OAuth2** — a ready-to-use, already-refreshed token; the refresh token is
  stripped before it reaches here. Read via ``.access_token`` / ``.token_type``
  / ``.expires_at``::

      {"access_token": "at-...", "expiration_time": "2026-07-23T10:00:00",
       "token_type": "Bearer"}

* **Database** — ``{"connection_string": "postgres://..."}``; read via
  ``.connection_string``.

A missing key is therefore a *connection-type* problem, not a nesting one: if
``.get("url")`` is ``None``, either the module declared the wrong ``app_types``
or it read a key name that type does not use. Do NOT silently flatten or guess —
raise a ``ManagedError`` whose message shows an EXAMPLE of the expected shape
(fake values) so the user can see what to fill in. See the connector guide's
Credentials section.

This class reads from both delivery locations so handlers never have to branch
on whether the connection was declared as a top-level ``connections`` block or
as an inline ``type: "connection"`` field.
"""

from __future__ import annotations

from typing import Any


class Credentials:
    """Typed, read-only view over a connection's delivered credentials."""

    def __init__(self, envelope: dict[str, Any] | None):
        self._envelope: dict[str, Any] = envelope or {}
        connection_data = self._envelope.get("connection_data")
        self._connection_data: dict[str, Any] = (
            connection_data if isinstance(connection_data, dict) else {}
        )
        value = self._connection_data.get("value")
        self._value: dict[str, Any] = value if isinstance(value, dict) else {}

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Credentials":
        """Build from a request body, checking both credential delivery paths.

        Uses the top-level ``credentials`` envelope when present; otherwise
        scans ``data`` for an inline connection field (a value carrying a
        ``connection_data`` block).
        """
        envelope = payload.get("credentials")
        if not envelope:
            data = payload.get("data")
            if isinstance(data, dict):
                for field_value in data.values():
                    if isinstance(field_value, dict) and "connection_data" in field_value:
                        envelope = field_value
                        break
        return cls(envelope if isinstance(envelope, dict) else None)

    # --- raw access ---------------------------------------------------------
    @property
    def value(self) -> dict[str, Any]:
        """The raw secret payload dict (``connection_data.value``) — the escape hatch."""
        return self._value

    def get(self, key: str, default: Any = None) -> Any:
        """Read a key directly out of the raw secret payload."""
        return self._value.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._value[key]

    def __contains__(self, key: str) -> bool:
        return key in self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    # --- API-key auth -------------------------------------------------------
    @property
    def api_key(self) -> Any:
        """The API key, accepting the common ``api_key``/``api_key_bearer`` names."""
        return self._value.get("api_key") or self._value.get("api_key_bearer")

    # --- OAuth2 auth --------------------------------------------------------
    @property
    def access_token(self) -> Any:
        """A ready-to-use OAuth access token (already refreshed by the platform)."""
        return self._value.get("access_token")

    @property
    def token_type(self) -> str:
        """The OAuth token type, defaulting to ``"Bearer"``."""
        return self._value.get("token_type") or "Bearer"

    @property
    def expires_at(self) -> Any:
        """Access-token expiry, accepting ``expiration_time``/``expires_at``."""
        return self._value.get("expiration_time") or self._value.get("expires_at")

    # --- Database auth ------------------------------------------------------
    @property
    def connection_string(self) -> Any:
        """A database connection string, when the credential provides one."""
        return self._value.get("connection_string")

    # --- Common envelope metadata ------------------------------------------
    @property
    def connection_app_type(self) -> Any:
        return self._connection_data.get("connection_app_type")

    @property
    def connection_id(self) -> Any:
        return self._connection_data.get("connection_id")

    @property
    def rate_limiter(self) -> Any:
        return self._connection_data.get("rate_limiter")

    @property
    def connection_management_type(self) -> Any:
        return self._envelope.get("connection_management_type")
