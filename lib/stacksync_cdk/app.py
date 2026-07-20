"""Flask app factory for a Stacksync connector.

``create_app(root)`` builds the connector's HTTP app by discovering modules on
disk and registering the three handlers each exposes. It runs *inside* the
connector; the CLI injects a tiny ``main.py`` that simply calls it.

Layout it expects::

    connector/
      stacksync.yml            # app-level settings only (no module list)
      modules/
        <module_type>/
          v<N>/
            schema.py          # def schema(request) -> SchemaResponse
            content.py         # def content(request) -> ContentResponse
            execute.py         # def execute(request) -> ExecuteResponse
            config.py          # optional: CONFIG = ModuleConfig(...)

Every version directory (``v1``, ``v2``, ...) is a separately routed module
version. The module id is derived as ``{app_type}-{module_type}-{version}``.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from types import ModuleType
from typing import Any, Callable

import yaml
from flask import Flask, current_app, jsonify, request

from stacksync_cdk.errors import ManagedError
from stacksync_cdk.module_config import ModuleConfig
from stacksync_cdk.request import Request
from stacksync_cdk.responses import ContentResponse, ExecuteResponse, Response, SchemaResponse

# A module version exposes up to three handlers; the file and its handler
# function share the kind's name (``schema.py`` -> ``def schema``, etc.).
_HANDLER_KINDS = ("schema", "content", "execute")

# A version directory is ``v`` followed by a number: v1, v2, v10, v1beta, ...
_VERSION_DIR = re.compile(r"^v\d\w*$")


@dataclass
class _DiscoveredModule:
    """One ``modules/<module_type>/v<N>/`` directory found on disk."""

    module_type: str
    version: str
    version_dir: str
    config: ModuleConfig


def _load_stacksync_yml(root: str) -> dict[str, Any]:
    path = os.path.join(root, "stacksync.yml")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _import_from_path(module_name: str, file_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_payload() -> dict[str, Any]:
    """The request body as a dict (empty when absent or not a JSON object)."""
    payload = request.get_json(silent=True, force=True)
    return payload if isinstance(payload, dict) else {}


def _module_id(app_type: str, module_type: str, version: str) -> str:
    """``{app_type}-{module_type}-{version}`` with dots normalized to underscores."""
    return f"{app_type}-{module_type}-{version.replace('.', '_')}"


def _parse_version(version_dir_name: str) -> str:
    """Turn a ``v<N>`` folder name into its version string (``v1`` -> ``1``)."""
    return version_dir_name[1:] if version_dir_name.startswith("v") else version_dir_name


def _load_module_config(version_dir: str, unique: str) -> ModuleConfig:
    config_path = os.path.join(version_dir, "config.py")
    if not os.path.isfile(config_path):
        return ModuleConfig()
    try:
        config_module = _import_from_path(f"{unique}_config", config_path)
    except Exception as error:  # a broken config.py must not sink the whole app
        logging.getLogger(__name__).warning("Could not load %s: %s", config_path, error)
        return ModuleConfig()
    candidate = getattr(config_module, "CONFIG", None)
    return candidate if isinstance(candidate, ModuleConfig) else ModuleConfig()


def _discover_modules(modules_dir: str) -> list[_DiscoveredModule]:
    """Find every ``modules/<module_type>/v<N>/`` version directory."""
    discovered: list[_DiscoveredModule] = []
    if not os.path.isdir(modules_dir):
        return discovered

    for module_type in sorted(os.listdir(modules_dir)):
        module_path = os.path.join(modules_dir, module_type)
        if not os.path.isdir(module_path) or module_type.startswith((".", "_")):
            continue
        for version_dir_name in sorted(os.listdir(module_path)):
            version_dir = os.path.join(module_path, version_dir_name)
            if not os.path.isdir(version_dir) or not _VERSION_DIR.match(version_dir_name):
                continue
            version = _parse_version(version_dir_name)
            unique = f"{module_type}_v{version}"
            discovered.append(
                _DiscoveredModule(
                    module_type=module_type,
                    version=version,
                    version_dir=version_dir,
                    config=_load_module_config(version_dir, unique),
                )
            )
    return discovered


def _load_handler(version_dir: str, kind: str, unique: str) -> Callable[..., Any] | None:
    """Import ``<kind>.py`` and return its ``<kind>`` handler function, if present."""
    path = os.path.join(version_dir, f"{kind}.py")
    if not os.path.isfile(path):
        return None
    handler = getattr(_import_from_path(f"{unique}_{kind}", path), kind, None)
    return handler if callable(handler) else None


def _schema_dict(result: Any) -> dict[str, Any]:
    """The dict placed under ``data.schema`` from a schema handler's return."""
    if isinstance(result, SchemaResponse):
        return result.to_schema_dict()
    if isinstance(result, dict):
        return result
    raise ManagedError.server_error(
        f"schema handler must return a SchemaResponse or dict (got {type(result).__name__})"
    )


def _content_wire(result: Any) -> dict[str, Any]:
    """The object placed under ``data`` from a content handler's return."""
    if isinstance(result, ContentResponse):
        return result.to_wire()
    if isinstance(result, dict):
        return result
    raise ManagedError.server_error(
        f"content handler must return a ContentResponse or dict (got {type(result).__name__})"
    )


def _execute_wire(result: Any) -> dict[str, Any]:
    """The full top-level response body from an execute handler's return."""
    if isinstance(result, ExecuteResponse):
        return result.to_wire()
    return {"data": result}


# Each kind wraps its handler's return into the endpoint's response envelope.
_WRAPPERS: dict[str, Callable[[Any], Any]] = {
    "schema": lambda result: Response.success({"schema": _schema_dict(result)}),
    "content": lambda result: Response.success(_content_wire(result)),
    "execute": lambda result: jsonify(_execute_wire(result)),
}


def _make_view(handler: Callable[..., Any], kind: str) -> Callable[[], Any]:
    """Build the Flask view for one handler: parse, run, wrap, and map errors."""
    wrap = _WRAPPERS[kind]

    def view() -> Any:
        try:
            return wrap(handler(Request(_parse_payload())))
        except ManagedError as error:
            return Response.error(error)
        except Exception as error:  # noqa: BLE001 - surfaced as a flat 500 envelope
            current_app.logger.exception("Unhandled error in %s handler", kind)
            return Response.error(error, status_code=500)

    return view


def _register_module(app: Flask, module: _DiscoveredModule) -> None:
    prefix = f"/{module.module_type}/v{module.version}"
    unique = f"{module.module_type}_v{module.version}"

    # Let handlers import sibling helper modules placed next to them.
    if module.version_dir not in sys.path:
        sys.path.insert(0, module.version_dir)

    registered: list[str] = []
    for kind in _HANDLER_KINDS:
        handler = _load_handler(module.version_dir, kind, unique)
        if handler is None:
            continue
        app.add_url_rule(
            f"{prefix}/{kind}",
            endpoint=f"{unique}_{kind}",
            view_func=_make_view(handler, kind),
            methods=["POST"],
        )
        registered.append(kind)

    if registered:
        app.logger.info(
            "Registered %s v%s: %s", module.module_type, module.version, ", ".join(registered)
        )
    else:
        app.logger.warning(
            "Module %s v%s: no schema.py, content.py, or execute.py handler found",
            module.module_type,
            module.version,
        )


def _app_config_route(root: str, modules: list[_DiscoveredModule]) -> Any:
    settings = _load_stacksync_yml(root).get("app_settings") or {}
    app_type = settings.get("app_type", "unknown_app")

    app_settings: dict[str, Any] = {
        "app_name": settings.get("app_name", "Unnamed App"),
        "app_type": app_type,
        "app_type_display": settings.get("app_type_display", settings.get("app_type")),
        "app_icon_svg_url": settings.get("app_icon_svg_url", ""),
        "app_description": settings.get("app_description", ""),
        "options": settings.get("options") or {},
    }

    module_dicts: list[dict[str, Any]] = []
    for module in modules:
        config = asdict(module.config)
        module_dicts.append(
            {
                "module_id": _module_id(app_type, module.module_type, module.version),
                "app_type": app_type,
                "module_type": module.module_type,
                "module_version": module.version,
                "module_category": config["module_category"],
                "module_name": config["module_name"]
                or module.module_type.replace("_", " ").title(),
                "module_description": config["module_description"],
                "supports_action": config["supports_action"],
                "supports_trigger": config["supports_trigger"],
                "requires_credentials_for_schema": config["requires_credentials_for_schema"],
                "module_icon_svg_url": config["module_icon_svg_url"],
                "module_path": f"{module.module_type}/v{module.version}",
            }
        )

    return jsonify({"data": {"app_settings": app_settings, "modules": module_dicts}})


def create_app(root: str | None = None) -> Flask:
    """Build the connector Flask app by discovering modules under ``root``.

    ``root`` defaults to the current working directory (where the injected
    ``main.py`` runs).
    """
    if root is None:
        root = os.getcwd()
    modules_dir = os.path.join(root, "modules")

    if not logging.root.handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.json.sort_keys = False  # preserve field/key order in every envelope

    app_type = (_load_stacksync_yml(root).get("app_settings") or {}).get("app_type", "unknown_app")
    app.logger.info("Initializing connector (root=%s, app_type=%r)", root, app_type)

    modules = _discover_modules(modules_dir)
    if not modules:
        app.logger.warning("No modules discovered under %s", modules_dir)
    for module in modules:
        _register_module(app, module)

    @app.get("/health")
    def health() -> Any:
        return Response.success({"status": "healthy"})

    @app.get("/app-config")
    def app_config() -> Any:
        return _app_config_route(root, modules)

    app.logger.info("Connector ready (%d module version(s))", len(modules))
    return app
