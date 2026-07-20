# Building a connector

A connector is a set of **modules**. Each module is a workflow step Stacksync can
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

## Project layout

```
connector/
  stacksync.yml            # app-level config (see below)
  requirements.txt         # the Stacksync CDK + your dependencies
  main.py                  # app = create_app(...) — the entry point
  gunicorn_config.py       # production serving
  Dockerfile               # deployment image
  modules/
    <module_type>/         # one folder per module (snake_case)
      v1/                  # a module version (see Versioning)
        schema.py  content.py  execute.py  config.py  context.md
```

Modules are **discovered from disk** — there is no module list anywhere. Adding a
`modules/<name>/v1/` folder adds a module.

## `stacksync.yml`

The connector's configuration — **app-level settings only**, in two blocks:

- **`deployment_settings`** — where it deploys:
  - `workspace` — your Stacksync workspace id (filled in by `stacksync connector create`)
  - `region` — `usnv` or `besg`
- **`app_settings`** — how the app appears in the workflow builder:
  - `app_type` — the stable machine id: lowercase letters, numbers, underscores (e.g.
    `acme_crm`). It's part of **every** module id, so don't change it after deploy.
  - `app_name` / `app_type_display` — the human-readable names
  - `app_icon_svg_url` — URL to an SVG icon
  - `app_description` — a one-line summary

That's the whole file — no modules are listed here.

## Versioning

Each module folder holds one or more version directories (`v1`, `v2`, …). The version
comes from the folder name and forms the module id `{app_type}-{module_type}-{N}`
(e.g. `acme_crm-create_records-1`).

- Start every module at **`v1`**.
- **Add a new version** when you make a **breaking** change to a module's inputs or
  behavior: create `modules/<name>/v2/` **alongside** `v1`. Both are served
  independently, so workflows already built on `v1` keep working while new workflows
  pick `v2`.
- **Non-breaking** changes (add an optional field, fix a bug, adjust a label) — just
  edit `v1` in place; no new version needed.

## How a module is used at runtime

1. A workflow editor adds your module to a workflow. Stacksync calls **`/schema`**
   to render the input form. As they fill fields, `/schema` may be called again to
   adapt the form (see the dynamic flow in [schema.md](schema.md)).
2. Fields with dynamic options call **`/content`** to populate their dropdowns.
3. When the workflow runs, Stacksync calls **`/execute`** with the input values and
   the connection's credentials, and stores what you return for downstream steps.

You never build the HTTP envelope — return a typed `SchemaResponse` /
`ContentResponse` / `ExecuteResponse` and the CDK wraps it correctly.

## The request

Every handler receives a typed `Request`. The platform posts a JSON body to each
endpoint; `Request` exposes the parts you need so you never dig through nested dicts.

### What each endpoint receives

**`/schema`** — the current form values (empty on first render):
```json
{ "data": { "form_data": { "select_object": "customer" } },
  "credentials": { ...envelope... } }
```
`request.form_data` → `{"select_object": "customer"}` · `request.credentials`

**`/content`** — plus which dropdowns to populate:
```json
{ "data": { "form_data": { ... }, "content_object_names": [ { "id": "objects" } ] },
  "credentials": { ...envelope... } }
```
`request.content_object_names` → `["objects"]` (ids normalized) · `request.form_data` · `request.credentials`

**`/execute`** — the user's input values directly under `data`:
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
`schema.py`. At runtime read it off `request.credentials`. The platform refreshes
OAuth tokens for you — you always get a valid `access_token`.

## Calling your system

The CDK ships **no** HTTP or database client — a database or storage connector
needs none. Make calls directly in the handler with whatever library fits
(`requests`, `httpx`, `psycopg2`, `boto3`), reading auth off `request.credentials`.

## Commands

```bash
stacksync connector run          # run locally against your workspace
stacksync connector deploy       # build and deploy
stacksync module create <name>   # scaffold a new module
```
