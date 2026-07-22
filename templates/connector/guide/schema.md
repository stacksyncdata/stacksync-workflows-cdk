# Skill: `schema`

```python
def schema(request: Request) -> SchemaResponse: ...
```

Returns the module's input form — the fields the workflow editor fills in.

## What you receive

- `request.form_data` — the values already entered (empty on first render). Read the
  object selector from here to decide which fields to add.
- `request.credentials` — the connection (may be empty; guard with `if request.credentials:`).

`schema` runs on every render, so it's a function — compute the form from
`form_data` and `credentials`.

## What you return

`SchemaResponse.from_schema(schema_dict)` for a full schema, or
`SchemaResponse(fields, connections=..., ui_options=..., metadata=...)` to assemble
one. Keep the static part (connections + selector) in a `BASE_SCHEMA` dict constant
and build only the dynamic fields in code.

## The object-selection pattern (two branches)

Most connectors expose an object selector whose choice loads that object's
fields via the `load_schema` round-trip, and wrap those fields in an array so a
workflow can create several records at once:

```python
BASE_SCHEMA = {
    "metadata": {"workflows_module_schema_version": "1.0.0"},
    "connections": {"required": True, "app_types": ["generic_api_credentials"],
                    "allowed_connection_management_types": ["managed"]},
    "fields": [{
        "id": "select_object", "type": "string", "label": "Select object",
        "validation": {"required": True},
        "on_action": {"load_schema": True},                       # re-runs schema() on change
        "content": {"content_objects": [{"id": "objects"}]},      # options from /content
        "ui_options": {"ui_widget": "SelectWidget"},
    }],
}

def schema(request):
    selected = request.form_data.get("select_object")
    if not selected:                                              # nothing picked → base
        return SchemaResponse.from_schema(BASE_SCHEMA)
    item_fields = fields_for(selected)                            # static OR fetched
    return SchemaResponse.from_schema(BASE_SCHEMA).add_record_array(selected, item_fields)
```

`add_record_array(object_name, item_fields)` wraps your per-record fields in a
`{object_name}s` array automatically (so a workflow can create several at once) —
you never hand-build that array. `fields_for(selected)` returns the object's fields:
a static list you define, or fetched from your API's metadata and mapped to
the field shapes below. Both are common (Rillet static; Zendesk/NetSuite fetched).

### Fetching fields from a metadata API

When the fields come from your API, read the connection off `request.credentials` in
the handler, call your metadata endpoint, and map each entry to a field dict:

```python
def schema(request):
    selected = request.form_data.get("select_object")
    if not selected:
        return SchemaResponse.from_schema(BASE_SCHEMA)
    item_fields = fields_for(selected, request.credentials)   # pass credentials in
    return SchemaResponse.from_schema(BASE_SCHEMA).add_record_array(selected, item_fields)

def fields_for(selected, credentials):
    meta = requests.get(
        f"{BASE_URL}/objects/{selected}/fields",
        headers={"Authorization": f"Bearer {credentials.api_key}"},
        timeout=30,
    ).json()
    return [to_field(m) for m in meta]     # map metadata → the field shapes below
```

Because this needs a live connection, set `requires_credentials_for_schema=True` in
`config.py` — that tells the platform to require a connection and deliver credentials
to `/schema`. Leave it `False` (the default) when the base schema renders without one.

## The golden rule for field types

Almost every field is `type: "string"` — numbers, dates, currency, and dropdowns
included — so users can type Jinja templates like `{{ MODULE.x.output.id }}` into any
field. Coerce to the real type in `execute`, not in the schema. Only `boolean`,
`array`, and `object` stay native.

### Dropdowns: `validation: {"pattern": ".*"}` (not `enum`)

Every dropdown carries `validation: {"pattern": ".*"}` instead of a JSON-Schema
`enum`. This is what lets a dropdown accept both:

- a value picked from the fetched/static options, and
- a value the user types — including a `{{ variable }}` / Jinja template from a
  previous step.

A hard `enum` would reject the template string (it isn't one of the listed options),
so the field would break for anyone wiring it from an earlier step. Use `pattern:
".*"` on every dropdown — both `content`-backed (options fetched fresh from your
`/content` endpoint each render) and `choices`-backed (inline static options). Add
`"required": True` alongside the pattern when the field is required.

## Field types

Omit `validation` entirely when a field isn't required; add `{"required": True}` when
it is.

Text (and long text — there is no textarea widget):
```python
{"id": "name", "type": "string", "label": "Name", "default": "",
 "validation": {"required": True}}
```

Number / integer / decimal / currency — string, coerced at write time:
```python
{"id": "amount", "type": "string", "label": "Amount", "default": ""}
```

Boolean — native; `disable_replacement` is required (else the UI renders an
`anyOf` wrapper instead of a checkbox):
```python
{"id": "active", "type": "boolean", "label": "Active", "default": False,
 "disable_replacement": True}
```

Date / datetime — string, no `format` (a picker would reject Jinja); hint the
format in the description:
```python
{"id": "due_date", "type": "string", "label": "Due date", "description": "Format: YYYY-MM-DD"}
```

Dropdown, static choices — options baked into the field:
```python
{"id": "priority", "type": "string", "label": "Priority",
 "ui_options": {"ui_widget": "SelectWidget"},
 "choices": {"values": [{"value": "low", "label": "Low"}, {"value": "high", "label": "High"}]},
 "validation": {"pattern": ".*"}}
```

Dropdown, dynamic options (reference / foreign-key / enum fetched at runtime) —
options come from `/content`; the `content_objects` id is the join key your
`content.py` handles:
```python
{"id": "customer", "type": "string", "label": "Customer",
 "ui_options": {"ui_widget": "SelectWidget"},
 "content": {"type": ["managed"], "content_objects": [{"id": "customers"}]},
 "validation": {"pattern": ".*"}}
```

Multi-select / tags — a comma-separated string (the array widget breaks the UI);
split it in `execute`:
```python
{"id": "tags", "type": "string", "label": "Tags", "description": "Comma-separated."}
```

Array (line items / batch records) — native; `items.ui_options.ui_order` is
required, and `default: [{}]` seeds one empty row:
```python
{"id": "line_items", "type": "array", "label": "Line items",
 "validation": {"required": True, "min_items": 1}, "default": [{}],
 "items": {"type": "object", "default": {}, "fields": item_fields,
           "ui_options": {"ui_order": [f["id"] for f in item_fields]}}}
```

Object (nested group) — native; `ui_order` required:
```python
{"id": "address", "type": "object", "label": "Address", "default": {},
 "fields": sub_fields, "ui_options": {"ui_order": [f["id"] for f in sub_fields]}}
```

JSON / free-form — a code editor:
```python
{"id": "config", "type": "string", "label": "Config",
 "ui_options": {"ui_widget": "CodeblockWidget", "ui_options": {"language": "json"}},
 "validation": {"pattern": ".*"}}
```

## Choice item shape

Everywhere — inline `choices.values` and the `/content` options — an option is
`{"value": ..., "label": ...}` (never `{id, label}` or `{const, title}`).

## Reacting to input changes: `on_action`

Add `on_action` to a field so changing it re-runs an endpoint:

- `{"load_schema": True}` — re-runs `/schema`. Use it on the object selector and
  any field whose value changes *which* fields appear.
- `{"load_content": True}` with `reload_content_objects` — re-runs `/content`
  to refresh dependent dropdowns. The field that changed lists which content
  objects to reload; the reloaded dropdown reads the parent's value from
  `request.form_data`.

Cascading dropdowns (pick a schema → reload the tables list):

```python
# parent: changing it reloads the "tables" dropdown
{"id": "schema_name", "type": "string", "ui_options": {"ui_widget": "SelectWidget"},
 "content": {"content_objects": [{"id": "schemas"}]},
 "on_action": {"load_content": True},
 "reload_content_objects": [{"id": "tables"}],
 "validation": {"pattern": ".*"}}

# child: options come from "tables"; picking one also rebuilds the form
{"id": "table_name", "type": "string", "ui_options": {"ui_widget": "SelectWidget"},
 "content": {"content_objects": [{"id": "tables"}]},
 "on_action": {"load_content": True, "load_schema": True},
 "validation": {"pattern": ".*"}}
```

A field can carry both `load_content` and `load_schema`.

## The connections block

```python
"connections": {
    "required": True,
    "app_types": ["generic_api_credentials"],     # the connection type(s) accepted
    "allowed_connection_management_types": ["managed"],
}
```
`app_types` is the connection type the module accepts — not a placeholder.
`generic_api_credentials` is a real, platform-registered connection (a box where the
user pastes an API key) — the sensible default for a custom connector that doesn't
have its own type. A connector with a dedicated connection type uses that instead,
exactly like the built-ins do: `["salesforce"]`, `["zendesk"]`, `["postgres"]`.

## Create vs update vs upsert

- Create: fields as above, `required` where the API requires it.
- Update (PUT is partial): strip `required` from all fields so an untouched field
  doesn't overwrite data; convert booleans to a 3-option select (`""` / `true` / `false`)
  so an untouched checkbox doesn't flip a value.
- Upsert: keep `required`, and prepend an optional `id` field to match existing records.

## Rules

- Deterministic for the same `(form_data, credentials)`.
- Never raise for a missing connection — return the base form so it still renders.
- Return the full form each time — the response replaces the current schema.

Next: [content.md](content.md) for dynamic dropdown options.
