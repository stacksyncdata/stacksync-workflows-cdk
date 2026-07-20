"""Managed (expected) errors.

Raise :class:`ManagedError` from a handler for any failure you want reported to
the user with a clean message and status code — invalid input, an upstream 4xx,
a missing record. Anything else that escapes a handler is treated as an
unexpected 500. Both are serialized to the platform's flat error envelope by
:class:`stacksync_cdk.responses.Response`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManagedError(Exception):
    """An expected error carrying a message, optional data/metadata, and a status."""

    error: str | Exception
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    status_code: int = 400

    def __str__(self) -> str:
        return str(self.error)

    @classmethod
    def validation_error(
        cls,
        error: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ManagedError":
        return cls(error=error, data=data or {}, metadata=metadata or {}, status_code=400)

    @classmethod
    def not_found(
        cls,
        resource: str,
        identifier: Any,
        metadata: dict[str, Any] | None = None,
    ) -> "ManagedError":
        return cls(
            error=f"{resource} not found: {identifier}",
            data={"resource": resource, "identifier": identifier},
            metadata=metadata or {},
            status_code=404,
        )

    @classmethod
    def unauthorized(
        cls,
        message: str = "Unauthorized access",
        metadata: dict[str, Any] | None = None,
    ) -> "ManagedError":
        return cls(error=message, metadata=metadata or {}, status_code=401)

    @classmethod
    def forbidden(
        cls,
        message: str = "Access forbidden",
        metadata: dict[str, Any] | None = None,
    ) -> "ManagedError":
        return cls(error=message, metadata=metadata or {}, status_code=403)

    @classmethod
    def server_error(
        cls,
        error: str | Exception,
        metadata: dict[str, Any] | None = None,
    ) -> "ManagedError":
        return cls(error=error, metadata=metadata or {}, status_code=500)
