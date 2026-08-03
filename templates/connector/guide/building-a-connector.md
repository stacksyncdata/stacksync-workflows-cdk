# Building a connector

Read [architecture.md](architecture.md) first — it defines how modules must be
structured. This page covers the mechanics: the files, the settings, the runtime
flow, and the request your handlers receive.

A connector is a set of modules. Each module is a workflow step Stacksync can
call. A module lives in `modules/<name>/v<N>/` and is made of at most three
handler functions — that's the whole surface:

| File | Function (typed) | Purpose | Skill |
|---|---|---|---|
| `schema.py`  | `schema(request: Request) -> SchemaResponse`   | the input form | [schema.md](schema.md) |
| `content.py` | `content(request: Request) -> ContentResponse` | dynamic dropdown options | [content.md](content.md) |
| `execute.py` | `execute(request: Request) -> ExecuteResponse` | the runtime action | [execute.md](execute.md) |
| `config.py`  | `CONFIG = ModuleConfig(...)` | module name / description / flags | — |
| `context.md` | — | the module's skill file — what the platform's AI needs to use it | [context.md](context.md) |

The function name matches the file name (`schema.py` → `def schema`).

Modules are discovered from disk — there is no module list anywhere. Adding a
`modules/<name>/v1/` folder adds a module. The project layout is in the README.

## `stacksync.yml`

The connector's configuration — app-level settings only, in two blocks:

- `deployment_settings` — where it deploys:
  - `workspace` — your Stacksync workspace id (filled in when the project is created)
  - `region` — `usnv` or `besg`
- `app_settings` — how the app appears in the workflow builder:
  - `app_type` — the stable machine id: lowercase letters, numbers, underscores (e.g.
    `acme_crm`). It's part of every module id, so don't change it after deploy.
  - `app_name` / `app_type_display` — the human-readable names
  - `app_icon_svg_url` — URL to an SVG icon
  - `app_description` — a one-line summary

That's the whole file — no modules are listed here.

## Module settings: `config.py`

Each module version ships a `config.py` exporting a `ModuleConfig`. Every field
has a sensible default — set only what differs:

```python
from stacksync_cdk import ModuleConfig

CONFIG = ModuleConfig(
    module_name="Create Records",
    module_description="Create one or more records of any object type.",
)
```

| Field | Default | What it does |
|---|---|---|
| `module_name` | folder name, titled | display name in the workflow builder |
| `module_description` | `""` | one-line description |
| `module_category` | `"action"` | module category |
| `requires_credentials_for_schema` | `False` | set True when `schema()` needs credentials (fields fetched from your API) |
| `on_content_update` | `True` | the engine re-fetches the schema with the node's form values at execution — required for dynamic schemas; their Jinja replacement depends on it |
| `on_content_initialized` | `True` | load dynamic content when the form first renders |
| `on_create` / `on_update` / `on_delete` | `False` | platform lifecycle hooks; leave off unless enabled for your app |

Leave `on_content_update` at `True` unless the module's schema is fully static:
disabling it on a dynamic module breaks variable replacement in the dynamically
added fields.

## Versioning

Each module folder holds one or more version directories (`v1`, `v2`, …). The version
comes from the folder name and forms the module id `{app_type}-{module_type}-{N}`
(e.g. `acme_crm-create_records-1`).

- Start every module at `v1`.
- Add a new version when you make a breaking change to a module's inputs or
  behavior: create `modules/<name>/v2/` alongside `v1`. Both are served
  independently, so workflows already built on `v1` keep working while new workflows
  pick `v2`.
- Non-breaking changes (add an optional field, fix a bug, adjust a label) — just
  edit `v1` in place; no new version needed.

## How a module is used at runtime

1. A workflow editor adds your module to a workflow. Stacksync calls `/schema`
   to render the input form. As they fill fields, `/schema` may be called again to
   adapt the form (see the dynamic flow in [schema.md](schema.md)).
2. Fields with dynamic options call `/content` to populate their dropdowns.
3. When the workflow runs, Stacksync calls `/execute` with the input values and
   the connection's credentials, and stores what you return for downstream steps.

You never build the HTTP envelope — return a typed `SchemaResponse` /
`ContentResponse` / `ExecuteResponse` and the CDK wraps it correctly.

## The request

Every handler receives a typed `Request`. The platform posts a JSON body to each
endpoint; `Request` exposes the parts you need so you never dig through nested dicts.

### What each endpoint receives

`/schema` — the current form values (empty on first render):
```json
{ "data": { "form_data": { "select_object": "customer" } },
  "credentials": { ...envelope... } }
```
`request.form_data` → `{"select_object": "customer"}` · `request.credentials`

`/content` — plus which dropdowns to populate:
```json
{ "data": { "form_data": { ... }, "content_object_names": [ { "id": "objects" } ] },
  "credentials": { ...envelope... } }
```
`request.content_object_names` → `["objects"]` (ids normalized) · `request.form_data` · `request.credentials`

`/execute` — the user's input values directly under `data`:
```json
{ "data": { "select_object": "customer", "customers": [ { "name": "A" } ] },
  "credentials": { ...envelope... },
  "workspace_id": "...", "workflow_id": "...", "workflow_module_instance_id": "..." }
```
`request.data` → the input values · `request.credentials`

### The credentials envelope

`credentials` always arrives in this shape:
```json
{ "connection_data": {
    "value": { ...the secret payload... },
    "connection_app_type": "hubspot",
    "connection_id": "...",
    "rate_limiter": { ... } },
  "connection_management_type": "managed" }
```

`request.credentials` unwraps it. The important part is `value`: it is a **flat
dict**, one level under `connection_data` — no deeper nesting, read your keys
straight off it. **Which keys are in `value` is defined by the connection type you
declared in `app_types` — not by your app.** Read that type's exact key names:

| Connection type | What `value` looks like | How to read it |
|---|---|---|
| `generic_api_credentials` (ships with the template) | **one** key only: `{"api_credentials": "..."}` — a single string (a key, a token, a connection string, or a JSON blob you `json.loads` yourself) | `request.credentials.get("api_credentials")` |
| A dedicated type | that type's exact form fields, e.g. `{"api_key": "...", "instance_url": "..."}` | `request.credentials.get("api_key")`, `.get("instance_url")`, … |
| OAuth2 | `{"access_token": "...", "expiration_time": "...", "token_type": "Bearer"}` (refresh token stripped) | `request.credentials.access_token` (already refreshed), `.token_type`, `.expires_at` |
| Database | `{"connection_string": "..."}` | `request.credentials.connection_string` |
| Metadata (on the envelope, not in `value`) | — | `request.credentials.connection_app_type`, `.connection_id`, `.rate_limiter` |

`request.credentials.api_key` is a convenience that reads `api_key` / `api_key_bearer`
off `value`; if your connection type stores the key under a different name, use
`.get("that_name")`.

Use `if request.credentials:` to check whether a connection is present (it's empty on
`/schema` and `/content` until the user selects one).

> **The #1 credentials mistake:** the template ships `generic_api_credentials`,
> which delivers a *single* `api_credentials` string. If your code reads named
> fields (`url`, `host`, `account_id`, …), they will always be missing. Either read
> everything out of that one `api_credentials` string, or ask Stacksync for a
> dedicated connection type that has the fields your app needs — then read its exact
> field names.

### When the shape isn't what you expect

A missing key is a **connection-type problem, not a nesting one**: if a key you
read is `None`, either the module declared the wrong `app_types` or it read a name
that type does not use. Never silently flatten or guess your way into the value —
that hides the real cause.

Instead, guard the keys you need and raise a `ManagedError` whose message shows an
**example of the expected shape with fake values** plus a one-line explanation. The
example is what makes the error in the Stacksync UI actionable — the user sees the
exact JSON to fill in, not just that something is missing:

```python
if not request.credentials.get("api_credentials"):
    raise ManagedError.validation_error(
        "This connection is missing its API credentials. Create a "
        "generic_api_credentials connection whose value looks like this:\n"
        '{"api_credentials": "your-api-key-here"}'
    )
```

Show the shape, never the real secret. Keep the example keys identical to the ones
your code reads (and to the connection type's real field names), so filling it in
fixes the error.

## Credentials

Declare what the module needs with the top-level `connections` block in
`schema.py`:

```python
"connections": {
    "required": True,
    "app_types": ["generic_api_credentials"],
    "allowed_connection_management_types": ["managed"],
}
```

`app_types` names the connection type your module accepts. There are two kinds —
this is the basic rule for credentials:

**1. The generic type — `generic_api_credentials` (ships with the template).**
Self-service: the user creates the connection and puts whatever your app needs
into a single `api_credentials` field — an API key, a URL, a connection string,
or a JSON blob. You decide what that string holds and read it with
`request.credentials.get("api_credentials")` (parse it yourself if it's JSON).
Use this to build and ship without waiting on anything.

**2. A dedicated Stacksync type — a specific `app_type` (e.g. `rillet`,
`postgres`, `zendesk`).** Stacksync provisions these: each defines its own named
fields and login style (API key, connection string, OAuth). They are registered
on the platform, not in your project. If the connection type you need for the app
you're developing isn't available yet, **reach out to Stacksync support** with the
app and how it authenticates, and we'll set it up and send you the `app_type` to
put in `app_types`. Then read its exact field names at runtime.

Start on the generic type; move to a dedicated type when you want named fields,
OAuth, or a branded connection experience for your users.

### Reading credentials at runtime

A workspace user creates the connection in Stacksync and selects it on your
module's step. Secrets are stored by Stacksync and delivered to your handlers at
runtime — never put credentials in your code or in `stacksync.yml`.

```python
api_key = request.credentials.api_key                  # API key or token
token   = request.credentials.access_token             # OAuth, already refreshed
dsn     = request.credentials.connection_string        # database connection string
value   = request.credentials.get("instance_url")      # any other field by name
```

For an OAuth connection type the platform refreshes tokens for you, so
`access_token` is always valid.

## Calling your system

The CDK ships no HTTP or database client — a database or storage connector
needs none. Make calls directly in the handler with whatever library fits
(`requests`, `httpx`, `psycopg2`, `boto3`), reading auth off `request.credentials`.

Next: [schema.md](schema.md) for the input form.
