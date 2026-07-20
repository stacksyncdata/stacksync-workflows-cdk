"""The typed output contracts — the CDK's one job on the way out.

A handler returns one of three response objects; the app factory wraps each in
the exact envelope fe-logics / the execution engine expect:

* :class:`SchemaResponse`  -> ``{"data": {"schema": {...}}}``
* :class:`ContentResponse` -> ``{"data": {"content_objects": [...]}}``
* :class:`ExecuteResponse` -> ``{"data": ..., "metadata"?: ..., "data_type"?: ...}``

Pydantic validates the well-defined parts on construction, so a connector can't ship
output the frontend won't render — a content option missing its ``label``, a field
without ``id``/``type``, a malformed ``connections`` block. The developer never has to
read the frontend to know the contract. The schema **fields** stay otherwise open
(only ``id``/``type`` are required) because the field DSL is open-ended and the
platform stores it unvalidated; every field type is documented in guide/schema.md.
"""

from __future__ import annotations

from typing import Any

from flask import Response as FlaskResponse
from flask import jsonify, make_response
from pydantic import BaseModel, ConfigDict, ValidationError

from stacksync_cdk.errors import ManagedError

DEFAULT_SCHEMA_VERSION = "1.0.0"


class _Field(BaseModel):
    """A schema field — ``id`` and ``type`` required, everything else open."""

    model_config = ConfigDict(extra="allow")
    id: str
    type: str


class _ContentOption(BaseModel):
    """A dropdown option — ``value`` and ``label`` required, extra keys allowed."""

    model_config = ConfigDict(extra="allow")
    value: Any
    label: str
    preview: str | None = None
    index: int | None = None


class _Connections(BaseModel):
    """The connections block — ``required`` and ``app_types`` required."""

    model_config = ConfigDict(extra="allow")
    required: bool
    app_types: list[str]
    allowed_connection_management_types: list[str] = []


def _validate_fields(fields: Any, *, where: str = "fields") -> None:
    """Check each field has ``id``/``type``, recursing into array items and objects."""
    if not isinstance(fields, list):
        raise ValueError(f"schema {where} must be a list, got {type(fields).__name__}")
    for i, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError(f"schema {where}[{i}] must be a dict")
        try:
            _Field.model_validate(field)
        except ValidationError as error:
            raise ValueError(f"schema {where}[{i}] is invalid: {error}") from error
        if field.get("type") == "array" and isinstance(field.get("items"), dict):
            _validate_fields(field["items"].get("fields", []), where=f"{where}[{i}].items.fields")
        elif field.get("type") == "object":
            _validate_fields(field.get("fields", []), where=f"{where}[{i}].fields")


def _validate_connections(connections: Any) -> None:
    if not isinstance(connections, dict):
        raise ValueError(f"connections must be a dict, got {type(connections).__name__}")
    try:
        _Connections.model_validate(connections)
    except ValidationError as error:
        raise ValueError(f"connections block is invalid: {error}") from error


class SchemaResponse:
    """A module's input schema, ready to be wrapped as ``{"data": {"schema": ...}}``.

    Pass the field list (the common case) plus optional ``connections`` /
    ``ui_options`` / ``metadata``; a default ``metadata.workflows_module_schema_version``
    is supplied when omitted. Fields are validated for ``id``/``type`` (only) and
    connections for its required keys. Use :meth:`from_schema` for a hand-built dict.
    """

    def __init__(
        self,
        fields: list[dict[str, Any]] | None = None,
        *,
        connections: dict[str, Any] | None = None,
        ui_options: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        fields = list(fields or [])
        _validate_fields(fields)
        if connections is not None:
            _validate_connections(connections)

        schema: dict[str, Any] = {}
        schema["metadata"] = metadata or {"workflows_module_schema_version": DEFAULT_SCHEMA_VERSION}
        if ui_options is not None:
            schema["ui_options"] = ui_options
        if connections is not None:
            schema["connections"] = connections
        schema["fields"] = fields
        self._schema = schema

    @classmethod
    def from_schema(cls, schema: dict[str, Any]) -> "SchemaResponse":
        """Wrap a complete, hand-built schema dict, validating fields and connections."""
        built = dict(schema or {})
        built.setdefault("metadata", {"workflows_module_schema_version": DEFAULT_SCHEMA_VERSION})
        built.setdefault("fields", [])
        _validate_fields(built.get("fields", []))
        if "connections" in built:
            _validate_connections(built["connections"])
        instance = cls.__new__(cls)
        instance._schema = built
        return instance

    def add_record_array(
        self,
        object_name: str,
        item_fields: list[dict[str, Any]],
        *,
        min_items: int = 1,
        label: str | None = None,
    ) -> "SchemaResponse":
        """Append an **array** field whose items hold ``item_fields`` — the standard
        object-selection shape used across connectors.

        The array's id is ``f"{object_name}s"`` and a workflow can submit several
        records per run. Returns ``self`` for chaining::

            return SchemaResponse.from_schema(BASE_SCHEMA).add_record_array(obj, fields)
        """
        _validate_fields(item_fields, where="item_fields")
        display = label or object_name.replace("_", " ").title()
        records_array = {
            "id": f"{object_name}s",
            "type": "array",
            "label": f"{display}s",
            "description": f"The {object_name} records to create.",
            "validation": {"required": True, "min_items": min_items},
            "default": [{}],
            "items": {
                "type": "object",
                "default": {},
                "ui_options": {"ui_order": [field["id"] for field in item_fields]},
                "fields": item_fields,
            },
        }
        self._schema["fields"] = [*self._schema.get("fields", []), records_array]
        return self

    def to_schema_dict(self) -> dict[str, Any]:
        """The schema dict placed under ``data.schema``."""
        return self._schema


class ContentResponse:
    """Dynamic dropdown options, ready to be wrapped as ``{"data": {"content_objects": [...]}}``.

    Pass the options in the constructor, keyed by content-object id (the common
    case)::

        ContentResponse({"record_type": [{"value": "deal", "label": "Deal"}]})

    Each option is validated for ``value`` and ``label`` (``preview`` optional; extra
    keys allowed); a stable ``index`` is assigned automatically. For paginated lists,
    use :meth:`add` with ``has_next_page`` instead.
    """

    def __init__(self, content_objects: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._objects: list[dict[str, Any]] = []
        for content_object_id, options in (content_objects or {}).items():
            self.add(content_object_id, options)

    def add(
        self,
        content_object_id: str,
        options: list[dict[str, Any]] | None = None,
        *,
        has_next_page: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> "ContentResponse":
        """Add one content object's options; returns ``self`` for chaining."""
        rows: list[dict[str, Any]] = []
        for index, option in enumerate(options or []):
            try:
                validated = _ContentOption.model_validate(option)
            except ValidationError as error:
                raise ValueError(
                    f"content option {index} for {content_object_id!r} is invalid "
                    f"(needs 'value' and 'label'): {error}"
                ) from error
            row = validated.model_dump()
            if row.get("preview") is None:
                row.pop("preview", None)
            if row.get("index") is None:
                row["index"] = index
            rows.append(row)

        # The frontend reads the object key as ``id`` on the primary populate path and
        # as ``content_object_name`` on the update-refresh path — emit both. Pagination
        # matches the ContentObjectResponsePagination type ({data, has_next_page}).
        content_object: dict[str, Any] = {
            "id": content_object_id,
            "content_object_name": content_object_id,
            "data": rows,
            "pagination": {"data": {}, "has_next_page": bool(has_next_page)},
        }
        if metadata is not None:
            content_object["metadata"] = metadata
        self._objects.append(content_object)
        return self

    def to_wire(self) -> dict[str, Any]:
        """The object placed under ``data`` (i.e. ``{"content_objects": [...]}``)."""
        return {"content_objects": self._objects}


class ExecuteResponse:
    """The result of running a module.

    ``data`` is the chainable payload downstream modules read as
    ``{{ MODULE.<id>.output }}`` — any JSON value (records, a URL, base64).
    ``metadata`` carries semantic extras like ``affected_records``;
    ``data_type`` is optional informational typing.
    """

    def __init__(
        self,
        data: Any = None,
        *,
        metadata: dict[str, Any] | None = None,
        data_type: str | None = None,
    ):
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError(
                f"ExecuteResponse metadata must be a dict, got {type(metadata).__name__}"
            )
        if data_type is not None and not isinstance(data_type, str):
            raise TypeError(
                f"ExecuteResponse data_type must be a string, got {type(data_type).__name__}"
            )
        self._data = data
        self._metadata = metadata
        self._data_type = data_type

    def to_wire(self) -> dict[str, Any]:
        """The full top-level response body (``data`` + optional metadata/data_type)."""
        wire: dict[str, Any] = {"data": self._data}
        if self._metadata is not None:
            wire["metadata"] = self._metadata
        if self._data_type is not None:
            wire["data_type"] = self._data_type
        return wire


class Response:
    """Raw success/error Flask responses in the platform's envelope."""

    @staticmethod
    def success(
        data: Any = None,
        metadata: dict[str, Any] | None = None,
        status_code: int = 200,
    ) -> FlaskResponse:
        """A success envelope: ``{"data": ..., "metadata"?: ...}``."""
        payload: dict[str, Any] = {"data": data}
        if metadata is not None:
            payload["metadata"] = metadata
        return make_response(jsonify(payload), status_code)

    @staticmethod
    def error(
        error: ManagedError | Exception | str,
        *,
        status_code: int | None = None,
    ) -> FlaskResponse:
        """A flat error envelope.

        For a :class:`ManagedError` the message, optional ``data``/``metadata``
        and its status are used. For anything else the response carries
        ``error``/``data``/``metadata``/``status_code`` at HTTP 500 (matching
        the previous CDK's unhandled-error shape).
        """
        if isinstance(error, ManagedError):
            payload: dict[str, Any] = {"error": str(error.error)}
            if error.data:
                payload["data"] = error.data
            if error.metadata:
                payload["metadata"] = error.metadata
            return make_response(jsonify(payload), error.status_code)

        code = status_code or 500
        payload = {
            "error": str(error),
            "data": {},
            "metadata": {},
            "status_code": code,
        }
        return make_response(jsonify(payload), code)
