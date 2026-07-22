# Architecture

Read this before writing any code. It defines how every Stacksync connector is
structured. Following it is what makes your connector behave like the native
ones; departing from it produces a connector that is hard to use and hard to
maintain.

## The rule

A module is one operation. The objects that operation applies to are chosen from
a dropdown inside the module, and both the form and the logic adapt to that
selection.

Do this:

```
modules/
  create_records/     one module. Object is a dropdown: Contact, Company, Deal
  update_records/
  upsert_records/
  delete_records/
  get_records/
  list_records/
```

Do not do this:

```
modules/
  create_contact/     wrong — an object is not an operation
  create_company/
  create_deal/
  update_contact/
```

Why it matters:

- One module per operation stays small and covers every object, including
  objects added later, with no new code.
- A module per object copies the same logic many times and fills the workflow
  builder with near-identical steps.
- The native connectors are built this way, so users already know the shape.

## The standard module set

Start with the operations your system actually supports. Most connectors need
some subset of:

| Module | What it does |
|---|---|
| `create_records` | create one or more records of the selected object |
| `update_records` | update existing records |
| `upsert_records` | create or update, matched on a key |
| `delete_records` | delete records |
| `get_records` | fetch specific records by id |
| `list_records` | list or search records |

Add a module for each operation you support, and only those your system can
actually perform. Each one is a folder, `modules/<operation>_records/v1/`, built
the same way as the reference module.

## Operations that are not CRUD

Some capabilities genuinely do not fit the pattern: running a report, triggering
a job, sending a raw API request. These get their own module, named for what
they do:

```
modules/
  execute_action/     run a named action in the external system
  get_report/         fetch a generated report
```

Use this for real exceptions. It is not an escape hatch for avoiding the object
dropdown.

## How the object dropdown works

This is the mechanism that lets one module serve every object. The form is built
in stages, and each stage is driven by what the user has filled in so far.

What the user sees:

1. The step opens showing the connection picker and a disabled object dropdown.
   The object dropdown needs a connection first, because its options — and the
   fields behind them — come from the connected system.
2. They pick a connection. The object dropdown becomes usable and Stacksync
   calls `/content` to fill it in.
3. They pick an object, for example Contact. Because that field is marked
   `on_action: {"load_schema": True}`, Stacksync immediately calls `/schema`
   again.
4. The form redraws with that object's fields, ready to fill in.

### 1. The base schema

`schema.py` holds a static base: the connection requirement and the object
selector. This is what renders before anything is chosen.

```python
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
            "validation": {"required": True},
            "ui_options": {"ui_widget": "SelectWidget"},
            "content": {"content_objects": [{"id": "objects"}]},
            "on_action": {"load_schema": True},
        }
    ],
}
```

Three parts do the work:

| Key | Effect |
|---|---|
| `connections.required` | the step cannot run until a connection is chosen |
| `content.content_objects` | the dropdown's options come from `/content`, under the id `objects` |
| `on_action.load_schema` | changing the selection re-runs `/schema` |

### 2. Filling the dropdown

`content.py` answers with the list of objects your connector supports. A static
list is fine; fetch it live when the system's objects vary per account.

```python
def content(request: Request) -> ContentResponse:
    return ContentResponse({
        "objects": [
            {"value": "contact", "label": "Contact"},
            {"value": "company", "label": "Company"},
        ]
    })
```

Every option is `{"value": ..., "label": ...}`. The value is what `execute`
receives later, so keep it a stable id.

### 3. Rebuilding the form for the selection

`schema.py` runs a second time with the selection in `request.form_data`. It has
two branches, and that is the whole pattern:

```python
def schema(request: Request) -> SchemaResponse:
    selected_object = request.form_data.get("select_object")

    # Nothing selected yet: show the base form.
    if not selected_object:
        return SchemaResponse.from_schema(BASE_SCHEMA)

    # An object is selected: return its fields.
    item_fields = get_fields_for(selected_object)   # static per object, or fetched
    return SchemaResponse.from_schema(BASE_SCHEMA).add_record_array(
        selected_object, item_fields
    )
```

`add_record_array` wraps those fields in an array named after the object, so a
workflow can submit several records in one run. Selecting Contact produces a
`contacts` array whose rows hold the contact fields. You do not build that
structure by hand.

If the fields must be fetched from the connected system, set
`requires_credentials_for_schema=True` in `config.py` so credentials are
delivered to `/schema`, then read them from `request.credentials`.

### 4. Running the operation

`execute.py` reads the same two values: which object was chosen, and the records
submitted for it.

```python
def execute(request: Request) -> ExecuteResponse:
    selected_object = request.data.get("select_object")
    records = request.data.get(f"{selected_object}s") or []

    created = [create_one(selected_object, record, request.credentials)
               for record in records]
    return ExecuteResponse(created, metadata={"affected_records": len(created)})
```

The object name is data, not code, so the same handler covers every object. When
you add support for a new object you extend the options and the field lookup —
you do not add a module.

The reference module `modules/create_records/v1/` implements exactly this. Copy
its shape for every new operation.

## Shared code belongs in utils

Anything used by more than one module goes in `utils/`, so modules stay thin and
consistent. The conventional pieces:

| File | Responsibility |
|---|---|
| `api_client.py` | HTTP calls, auth headers, retries, error handling |
| `field_builders.py` | turn the system's field metadata into schema fields |
| `content_handler.py` | build dropdown options |
| `payload_transformer.py` | map submitted form values into the API's payload |

A module should read as: gather inputs, call a util, return a response. If a
module contains request plumbing or field-mapping logic, move it to `utils/`.

## Naming

- Module folders are snake_case and name the operation: `create_records`.
- Every module lives under a version folder: `modules/create_records/v1/`.
- Handler function names match their file: `schema.py` defines `schema`.

## Checklist before you build

- One module per operation, never per object.
- Objects selected from a dropdown inside the module.
- Non-CRUD capabilities get their own clearly named module.
- Shared logic in `utils/`, not copied between modules.
- Each module in its own `modules/<name>/v1/` folder.

Next: [building-a-connector.md](building-a-connector.md) for the files, the
runtime flow, and how to read credentials.
