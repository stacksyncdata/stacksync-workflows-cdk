"""Input form for the Create Records module.

The object-selection pattern used across Stacksync connectors, in two branches:

  - Nothing selected yet → the base schema (the object selector).
  - An object selected    → the object's fields, wrapped in an array so a workflow
                            can create several records at once (via add_record_array).

The object's fields can be a static list or fetched from your API — both are common
(Rillet defines them statically; Zendesk fetches ticket fields live).
See ../../../guide/schema.md for every field type.
"""

from stacksync_cdk import Request, SchemaResponse

# The static base schema: the connections block and the object selector. Its
# options come from content.py; changing it re-runs schema() (on_action.load_schema).
BASE_SCHEMA = {
    "metadata": {"workflows_module_schema_version": "1.0.0"},
    "connections": {
        "required": True,
        "app_types": ["generic_api_credentials"],
        "allowed_connection_management_types": ["managed"],
    },
    "fields": [
        {
            "id": "select_object",
            "type": "string",
            "label": "Select object",
            "description": "Choose the type of record to create.",
            "validation": {"required": True},
            "on_action": {"load_schema": True},
            "content": {"content_objects": [{"id": "objects"}]},
            "ui_options": {"ui_widget": "SelectWidget"},
        }
    ],
}


def schema(request: Request) -> SchemaResponse:
    selected_object = request.form_data.get("select_object")

    # Nothing selected yet → base schema.
    if not selected_object:
        return SchemaResponse.from_schema(BASE_SCHEMA)

    # An object is selected → its fields, auto-wrapped in a batch array.
    # TODO: return the fields for `selected_object` — a static list per object, or
    #       fetched from your API using request.credentials.
    item_fields = [
        {"id": "name", "type": "string", "label": "Name", "validation": {"required": True}},
    ]
    return SchemaResponse.from_schema(BASE_SCHEMA).add_record_array(selected_object, item_fields)
