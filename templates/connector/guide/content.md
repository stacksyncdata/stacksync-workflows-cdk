# Skill: `content`

```python
def content(request: Request) -> ContentResponse: ...
```

Populates the dynamic dropdown options for fields that declare
`content.content_objects` in the schema (the `select_object` selector, plus any
foreign-key / enum dropdowns your object fields use).

## What you receive

- `request.content_object_names` — the ids to populate this call (each is a schema
  field's `content.content_objects[].id`). Build only what's asked for.
- `request.form_data` — the current field values (for dependent dropdowns).
- `request.credentials` — the connection (may be empty).

## What you return

`ContentResponse`, keyed by content-object id. Each option is `{"value", "label"}`
(`preview` optional). `label` is what the editor sees; `value` is what's stored and
reaches `execute` in `request.data` — it's usually a scalar id (a string), but the
platform accepts any JSON, so a composite `{"key": ..., "value": ...}` works too.
The CDK adds the `index` and the object envelope (id / content_object_name /
pagination) for you — you only supply `value` + `label`:

```python
def content(request):
    content_objects = {}
    for name in request.content_object_names:
        if name == "objects":
            content_objects["objects"] = object_types()          # static or fetched
        elif request.credentials:
            content_objects[name] = fetch_options(name, request.credentials)  # FK/enum
    return ContentResponse(content_objects)
```

## Two kinds of options

Real connectors keep a small registry mapping each content-object id to how its
options are produced:

- Static list (an "enum") — a fixed `[{"value","label"}]` you define. Fastest;
  no API call. Example: a `choices_currency` dropdown, or the `objects` selector.
- Fetched (a "foreign key") — call your API, then map each record to an option.
  When mapping, pick the value and label defensively:

```python
def fetch_options(name, credentials):
    records = api_list(REGISTRY[name]["endpoint"], credentials)   # your API call
    out = []
    for rec in records:
        value = rec.get("id") or rec.get("key") or rec.get("name")   # first non-empty
        if value is None:
            continue
        label = rec.get("name") or str(value)                        # human label
        out.append({"value": str(value), "label": label})
    return out
```

## The `objects` selector

The `objects` dropdown (the `select_object` options) is usually a fixed list of the
object types your connector supports — but it can be fetched too (a database
connector lists its tables). Filter by the operation this module supports:

```python
OBJECTS = [{"value": "customer", "label": "Customer"}, {"value": "invoice", "label": "Invoice"}]
```

## Dependent dropdowns

When one dropdown's options depend on another field, read the parent value from
`request.form_data` and filter:

```python
team = request.form_data.get("team")
content_objects["project"] = projects_for(team, request.credentials)
```

A common lighter form is a fixed filter baked into the fetch (e.g. only users with
`role=agent` for an "assignee" dropdown).

## Pagination

For long lists, page from your API and mark more with `.add(..., has_next_page=True)`:

```python
response = ContentResponse()
options, more = fetch_page(name, cursor, request.credentials)
response.add(name, options, has_next_page=more)
return response
```

Most dropdowns are modest — fetch one generous page and don't paginate unless needed.

## Rules

- Never raise. `content` must not crash the form. On no credentials or an upstream
  error, return empty options for that name: `if not request.credentials: return ContentResponse()`.
- Set timeouts, handle upstream failures per-name, never log secrets.
- `value` is stored and reaches `execute` in `request.data` — keep it stable (an id),
  not a display string.

Next: [execute.md](execute.md) for the action that runs.
