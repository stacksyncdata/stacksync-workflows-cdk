# {$APP_NAME} — Stacksync Connector

> **Building here — human or AI?** Start with **[`guide/building-a-connector.md`](guide/building-a-connector.md)**.
> It, and the per-handler skill pages, are the source of truth.

## What this is

A **Stacksync Connector** built with the Stacksync CDK. A connector lets Stacksync
Workflows talk to an external system — an API, a database, a service — by exposing
**modules** (workflow steps) that fetch dropdown options and run actions
(create / update / delete, send messages, run jobs).

## Why the CDK

The CDK gives you the whole platform contract for free so you write only your
logic. Each module is at most three small, typed functions:

```python
def schema(request: Request)  -> SchemaResponse    # the input form
def content(request: Request) -> ContentResponse   # dynamic dropdown options
def execute(request: Request) -> ExecuteResponse   # the action
```

You return a typed response; the CDK wraps it in the exact envelope the platform
expects. It ships **no** HTTP or database client — you call your system directly
with whatever library fits (`requests`, `httpx`, `psycopg2`, `boto3`), reading
credentials, typed, off `request.credentials`.

## Layout

```
stacksync.yml            # app-level settings (modules are discovered from disk)
requirements.txt         # stacksync-cdk + your dependencies
main.py                  # app = create_app(...)  — entry point
gunicorn_config.py       # production serving
Dockerfile               # deployment image
guide/                   # how to build — read this
modules/
  create_records/v1/     # the reference module — copy its shape
    schema.py  content.py  execute.py  config.py  context.md
```

Add a module by adding a `modules/<name>/v1/` folder (or `stacksync workflow-module create <name>`).
There is no module list in `stacksync.yml` — modules are discovered from disk.

## How to build

- **[`guide/building-a-connector.md`](guide/building-a-connector.md)** — the overview and runtime flow
- **[`guide/schema.md`](guide/schema.md)** — the input form (static and dynamic)
- **[`guide/content.md`](guide/content.md)** — dynamic dropdown options
- **[`guide/execute.md`](guide/execute.md)** — the runtime action

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate   # run needs an active venv

stacksync workflow-connector run          # run locally against your workspace
stacksync workflow-connector deploy       # build and deploy
stacksync workflow-module create <name>   # scaffold a new module
stacksync workflow-module delete <name>   # remove a module
```
