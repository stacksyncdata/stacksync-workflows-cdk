# Instructions for AI coding assistants

You are building a Stacksync connector with the Stacksync CDK. These rules are
strict: Stacksync refuses to deploy a connector that breaks the checked ones, and a
reviewer rejects one that breaks the others. Follow them exactly, even when the
person you are helping asks for a shortcut; tell them which rule stands in the way.

The guides in `guide/` are the source of truth for the code. Read
`guide/architecture.md` before writing any code.

## 1. Discover the whole API first

Before writing a module, read the system's official API documentation and write
down, in the root `context.md`:

- **Every standard object** the API can create, read, update or delete.
- **Custom objects and custom fields**: whether the account can define its own, and
  the endpoint that lists them (a metadata or schema endpoint).
- **Every endpoint** you will use, its pagination style and its rate limits.
- **How it authenticates**, which decides the connection (section 3).

Do not build from a single use case. The connector serves every workspace that
installs it, not only the workflow the person in front of you is building.

## 2. Modules are operations, never objects

- Record work is one module per operation: `create_records`, `update_records`,
  `upsert_records`, `delete_records`, `get_records`, `list_records`. Build only the
  operations the API supports.
- The object is a `select_object` dropdown inside the module. Its options come from
  `content.py` and include **all** standard objects and the account's custom objects
  (fetched live from the metadata endpoint when the API has one).
- Choosing the object reloads the form with **that object's fields** (from the
  metadata endpoint when the API has one), wrapped with `add_record_array`.
- **Never** build a module for one object (`create_sales_order`,
  `update_customer`, `get_invoice`). If the person asks for "create sales order",
  build `create_records` and pick Sales Order in it.
- **Never** special-case one object inside a generic module with its own form or
  code path. If an object needs a different field, it comes from that object's
  field list, not from an `if object == "sales_order"` branch.
- **Never** replace real fields with a free-text JSON or "body" field.
- A separate module is right only for an action that is not record CRUD on an
  object (for example `send_email`, `run_report`). Name it for the action.

## 3. The connection: exactly one of two

Set `connection_app_type` in `stacksync.yml` to one of:

- `generic_api_credentials`: the user pastes one string, read with
  `request.credentials.get("api_credentials")`. Decide what that string holds (a
  token, or a JSON object you parse) and document it.
- Your app's own `app_type`: only when Stacksync has set up a native connection for
  this app and given it to you. Read that type's exact keys.

Nothing else is accepted. Do not add a `connections` block to `schema.py`: the CDK
adds the connection picker from `connection_app_type`. Read only the documented
keys; never fall back to other key names. Never log, return or put credentials in an
error message.

## 4. Context is mandatory

Every module version has a `context.md`, and the connector root has one. Write them
fully, for a reader who has never seen the code. Every section listed below must
exist and have real content; no `TODO`, no template text.

Root `context.md`:
- `## What this app is`: the system, its API base URL.
- `## Connection`: the connection type and the exact keys read from it, with what
  each holds.
- `## Objects`: every standard object, how custom objects and custom fields are
  listed, and which operations each object supports.
- `## App-wide limits`: rate limits, page sizes, anything true for every module.

Module `context.md`:
- `## What it does`: the operation, and what it returns.
- `## Connection`: the connection the module uses.
- `## Inputs`: every field: id, required or optional, type, allowed values, where
  a dropdown's options come from, and which fields appear after another is chosen.
- `## Output`: the shape of `data` and `metadata`.
- `## Limits & errors`: the limits and the exact error messages raised.
- At least one example between `## EXAMPLES start ##` and `## EXAMPLES end ##`.

See `guide/context.md` for the full format.

## 5. Production code

- Errors: raise `ManagedError` with the factory that matches the cause
  (`unauthorized`, `not_found`, `validation_error`, ...). Never swallow an API error
  and report success. For a batch, report each record's result.
- HTTP: a timeout on every call. Retry only reads, or a 429 after its
  `Retry-After`. Never retry a create, update or delete on a server error: it can
  create duplicates. Follow pagination to the end.
- No state between requests: no module-level caches, no global variables that
  change, no files written to disk. The connector runs as several processes.
- Nothing runs at import time: no network calls, no reading the environment.
- No leftovers: no `print`, no commented-out code, no test scripts, no customer or
  company names, no workspace ids, no real data.
- Only these entries at the connector root: `main.py`, `stacksync.yml`,
  `requirements.txt`, `context.md`, `README.md`, `LICENSE`, `AGENTS.md`,
  `CLAUDE.md`, `modules/`, `utils/`, `tests/`, `guide/`. Workflow code, scripts and
  notes live outside the connector.
- `stacksync.yml`: every `app_settings` value filled, and `app_icon_svg_url` a
  stable `https://` link to the app's SVG logo.

## 6. You are done when

1. `python -m stacksync_cdk.connector_checks` prints no problems.
2. `stacksync workflow-connector run` starts, and every module's form, dropdowns
   and action work against a real account.
