"""Per-module capability metadata.

The platform (fe-logics / frontend / execution engine) needs a small amount of
metadata about each module — its display name, whether it is an action, whether
its ``/schema`` can render without a live connection, and so on. Because a
connector declares its modules in code (no ``module_schema.yml``), each module
version optionally ships a ``config.py`` exporting a ``ModuleConfig``:

    # modules/create_records/v1/config.py
    from stacksync_cdk import ModuleConfig

    CONFIG = ModuleConfig(
        module_name="Create Records",
        module_description="Create one or more records.",
        requires_credentials_for_schema=False,
    )

The module version (``v1``) comes from the folder name, not from here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModuleConfig:
    """Declarative capability flags surfaced to the platform via ``/app-config``.

    ``supports_trigger`` is reserved for forward-compatibility; the connector
    layer does not implement runtime triggers today.
    """

    module_name: str | None = None
    module_description: str = ""
    module_category: str = "action"
    supports_action: bool = True
    supports_trigger: bool = False
    requires_credentials_for_schema: bool = False
    module_icon_svg_url: str | None = None
