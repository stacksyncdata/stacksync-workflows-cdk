# {$APP_NAME} — Stacksync Connector

A connector lets Stacksync Workflows talk to an external system: an API, a
database, or a service. This project is a working template. Rename it, fill in
the parts that call your system, and deploy it.

Building here, whether you are a developer or an AI assistant? Read
[`guide/architecture.md`](guide/architecture.md) first. It defines the structure
every connector must follow, and it is the source of truth.

## How a connector works

A connector is a set of modules. A module is one step a workflow can run, such
as "Create records", and is a folder of small handler functions: the input form,
the dropdown options, and the action that runs.

The CDK ships no HTTP or database client. You call your system with whatever
library fits (`requests`, `httpx`, `psycopg2`, `boto3`) and read credentials off
the request. The guide covers all of it.

## Project layout

```
stacksync.yml          app settings (name, type, workspace)
requirements.txt       the Stacksync CDK plus your dependencies
main.py                the entry point
guide/                 how to build — read this
utils/                 shared helpers you add (API client, field builders)
modules/
  create_records/v1/   the reference module — copy its shape
```

Modules are discovered from disk. Adding a `modules/<name>/v1/` folder adds a
module; nothing is registered in `stacksync.yml`.

## The one rule

A module is one operation, not one object. Build `create_records` with the
object picked from a dropdown inside it — not `create_contact`, `create_company`
and `create_deal`. Shared code goes in `utils/`.

This is what keeps a connector small and consistent with the native ones.
[`guide/architecture.md`](guide/architecture.md) explains it in full and is
required reading before you write code.

## Build it

Start by naming your connector in `stacksync.yml`: set `app_type` (a stable id
such as `acme_crm`) and `app_name` (what users see in the workflow builder).

Then read the guide in this order:

1. [`guide/architecture.md`](guide/architecture.md) — how modules must be structured
2. [`guide/building-a-connector.md`](guide/building-a-connector.md) — the files, the
   runtime flow, and how to read credentials
3. [`guide/schema.md`](guide/schema.md) — the input form
4. [`guide/content.md`](guide/content.md) — dynamic dropdown options
5. [`guide/execute.md`](guide/execute.md) — the action that runs

Then fill in `modules/create_records/v1/`, run it locally, and deploy.

## Commands

```bash
stacksync workflow-module create <name>     # add a module
stacksync workflow-connector run            # run locally against your workspace
stacksync workflow-connector deploy         # deploy to your workspace
stacksync workflow-module delete <name>     # remove a module
```

`run` creates and manages a local virtual environment for you.
