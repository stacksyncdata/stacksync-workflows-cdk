# Skill: `execute`

```python
def execute(request: Request) -> ExecuteResponse: ...
```

Runs the module: reads the input, calls your API, returns the result.

## What you receive

- `request.data` — the input values. For the object-selection pattern that's
  `select_object` plus the records array under `f"{select_object}s"`:
  ```python
  selected = request.data.get("select_object")
  records = request.data.get(f"{selected}s") or []
  ```
- `request.credentials` — the connection, typed:
  - API key → `request.credentials.api_key`
  - OAuth2 → `request.credentials.access_token` (already refreshed by the platform)
  - Database → `request.credentials.connection_string`
  - raw dict → `request.credentials.value`

## Validate early

```python
if not selected:
    raise ManagedError.validation_error("select_object is required.")
if not records:
    raise ManagedError.validation_error(f"At least one {selected} is required.")
```

## Coerce the string-typed values back

The schema sends numbers, dates, booleans, and multi-selects as strings (so Jinja
works), so `execute` must convert each record to your API's real types before the
call. Leave `{{ … }}` templates untouched (they're already resolved by the engine, but
a literal template that slipped through must not crash a cast):

```python
def to_api(record):
    out = {}
    for key, value in record.items():
        if value in ("", None):
            continue                                   # drop empties (partial update-safe)
        if value in ("true", "false"):
            out[key] = value == "true"                 # string → bool
        elif key in ARRAY_KEYS and isinstance(value, str):
            out[key] = [s.strip() for s in value.split(",") if s.strip()]   # comma → list
        elif key in NUMERIC_KEYS and str(value).lstrip("-").isdigit():
            out[key] = int(value)                      # string → int/float
        else:
            out[key] = value
    return out
```

Also pack any dynamic custom fields (e.g. `custom_field_{id}` → `{"id": int(id),
"value": …}`) and wrap the record in the API's envelope if it needs one (e.g.
`{"ticket": {…}}`).

## Call the API — per-record vs bulk

Create the records. Two shapes are common:

- Per-record, concurrent — a thread pool (cap ~5) submitting one call per record,
  results collected in input order. Works for any API.
- Bulk — when there's a create-many endpoint and you have >1 record, send them in
  one call.

Aggregate into a result: `{"total", "successful", "failed", "results": [...]}`, where
each result row is `{"index", "status": "success"|"failed", ...}` (failed rows carry an
`error` message). A per-record failure should not abort the batch — record it and
continue.

## Return

```python
return ExecuteResponse(result, metadata={"affected_records": result["successful"]})
```

`data` is what downstream steps read as `{{ MODULE.<id>.output }}`. On partial failure,
still return the full breakdown so the user can see which records failed — either as
data, or via a `ManagedError` whose `data` carries the result.

## Errors

- Expected failures → `raise ManagedError.validation_error(...)` / `.not_found(...)` /
  `.unauthorized(...)`. The message reaches the user cleanly.
- Anything else becomes a 500 automatically — don't wrap the whole body in try/except
  just to swallow it.
- Don't retry mutating calls on a 500 — a create may have succeeded server-side, and
  a retry would duplicate it.

## Output chaining

The engine stores your `data` and exposes it to later steps as
`{{ MODULE.<this_module_id>.output.<field> }}`. Return a clean, predictable shape.
There is no output schema to declare.

## Rules

- Validate required inputs early with clear messages.
- Coerce strings back to real types before the API call; set timeouts.
- Never log secrets.
