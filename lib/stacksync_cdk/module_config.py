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

    # Action hooks, mirroring the native module registry's module_actions_schema.
    #
    # on_content_update — the engine re-fetches this module's input schema, with
    # the node's current form values and credentials, at execution time. Required
    # for any module whose schema depends on the form (the object-selection
    # pattern): without the re-fetch, dynamically added fields are missing from
    # the schema and their Jinja placeholders are never replaced. Leave True
    # unless the module's schema is fully static and the extra call matters.
    #
    # on_content_initialized — load the module's dynamic content when the form
    # first renders in the workflow builder.
    #
    # on_create / on_update / on_delete — platform lifecycle hooks; off by
    # default and only meaningful when the corresponding behavior is enabled
    # for your app by Stacksync.
    on_content_update: bool = True
    on_content_initialized: bool = True
    on_create: bool = False
    on_update: bool = False
    on_delete: bool = False
