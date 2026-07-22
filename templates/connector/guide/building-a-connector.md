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
| `context.md` | — | what the module does (for humans + AI) | — |

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
`request.credentials` unwraps it. Read it typed by auth style:

| Auth style | How to read it |
|---|---|
| API key | `request.credentials.api_key` |
| OAuth2 | `request.credentials.access_token` (already refreshed), `.token_type`, `.expires_at` |
| Database | `request.credentials.connection_string` |
| Anything else | `request.credentials.get("field")` — read any key by name (e.g. an instance URL); `request.credentials.value` is the raw dict |
| Metadata | `request.credentials.connection_app_type`, `.connection_id`, `.rate_limiter` |

Use `if request.credentials:` to check whether a connection is present (it's empty on
`/schema` and `/content` until the user selects one).

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

`app_types` names the connection type your module accepts.

### Getting your connection type

Every app on Stacksync has its own connection type — `rillet`, `postgres`,
`zendesk`, and so on. It defines what the user fills in when they connect, and
whether the login is an API key, a connection string, or an OAuth flow.

Connection types are registered on the platform, so they are not defined in your
project. Stacksync provides the connection type for your app when you start
building: contact us with the app you are connecting to and how it
authenticates, and we will set it up and send you the type to use. Put that
value in `app_types`.

Self-service connection creation is on the way; until then this step is done for
you.

The template ships with `generic_api_credentials`, a general-purpose type that
accepts any non-expiring secret — an API key, a token, a connection string, or a
JSON credentials file. It is useful for getting started before your own type is
ready.

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
