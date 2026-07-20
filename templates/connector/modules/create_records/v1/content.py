"""Dynamic dropdown options for the Create Records module.

Populates the ``objects`` selector declared in ``schema.json``, and any reference
(foreign-key / enum) dropdowns your object fields declare. Return an empty
``ContentResponse`` when there is no connection yet. See ../../../guide/content.md.
"""

from stacksync_cdk import ContentResponse, Request


def content(request: Request) -> ContentResponse:
    content_objects: dict[str, list[dict]] = {}

    for name in request.content_object_names:
        if name == "objects":
            # The object types this module can create. Return a static list, or fetch
            # them from your API using request.credentials (e.g. DB connectors list
            # their tables). TODO: [{"value": ..., "label": ...}]
            content_objects["objects"] = []
            continue

        # Any other requested name is a reference dropdown from an object's fields.
        if request.credentials:
            # TODO: fetch its options from your API → [{"value": ..., "label": ...}].
            content_objects[name] = []

    return ContentResponse(content_objects)
