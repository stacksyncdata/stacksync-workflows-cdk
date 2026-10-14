# `context.md` — the module's skill file

`context.md` is how a module explains itself to Stacksync's AI. It is not code and
has no handler: it is one markdown document, served at `/context`, that Stacksync's
AI reads to choose the module, fill its form, and run it. A module with a good
`context.md` gets configured and wired correctly by the AI; one without it is used
blind.

Write it well: the quality of this file affects how reliably the AI uses your module
far more than anything else.

## Two levels

- **Module-level** — `modules/<name>/v<N>/context.md`, served at
  `/<name>/v<N>/context`. Describes that one module version. This is where almost
  all content goes.
- **App-level** — `context.md` at the connector root, served at `/context`.
  Required. What the app is, its connection, its objects, and what is true for
  **every** module (limits, conventions). The platform prepends it to each module.

Both are required and served raw.

## What to provide (required)

Describe the module the way you'd describe a tool to a capable colleague who has
never seen your code — in the third person, concretely. **Deployment is refused**
while a required section is missing, empty, or still has a `TODO`, so check before
you deploy:

```
python -m stacksync_cdk.connector_checks
```

**App-level `context.md`** (connector root):

| Section | Required | What goes in it |
|---|---|---|
| **What this app is** | yes | The system and the API it calls (base URL). |
| **Connection** | yes | The connection type (`connection_app_type`) and the exact keys read from it, with what each holds. |
| **Objects** | yes | Every standard object, how the account's custom objects and custom fields are listed, and which operations each object supports. |
| **App-wide conventions** | no | Only what is true for every module. |
| **App-wide limits** | yes | Rate limits, page sizes, and the error each limit produces. |

**Module `context.md`** (`modules/<name>/v<N>/`):

| Section | Required | What goes in it |
|---|---|---|
| **What it does** | yes | The task, the API operation, and **what it returns**. |
| **When to use it / when not to** | no | The right scenarios, and where a different module fits. |
| **Connection** | yes | The connection the module uses and the keys it reads. |
| **Inputs** | yes | One line per field: id, required/optional, type, allowed values / exact encoding, where a dropdown's options come from, and which fields appear after another is chosen. |
| **Output** | yes | The shape of `data` and `metadata`. |
| **Limits & errors** | yes | Hard limits, the **exact** error string raised, and how to avoid it. |
| **Prerequisites & order** | no | Sequencing rules, e.g. "confirm the vendor exists before creating a bill." |
| **Examples** | yes | At least one, between the `EXAMPLES` markers — see the format below. |

These principles come from how tool descriptions are written for AI agents: state
what it does *and returns*, be explicit about when (and when not) to use it, describe
every input, and show concrete examples for anything format-sensitive.

## The examples block

Keep worked examples inside `## EXAMPLES start ##` / `## EXAMPLES end ##`. Each
example is a short scenario, the filled input values in the `changes[]` shape the
copilot produces, and per-field notes:

```
## EXAMPLES start ##
### <scenario>
FORM DATA:
{ "summary": "...", "changes": [ { "field_id": "...", "field_value": "...", "reason": "...", "summary": "..." } ] }
COMMENTS:
`field_id` -> gotcha
## EXAMPLES end ##
```

## Rules

- **One module, one purpose** — a focused module is used correctly far more often
  than a do-everything one; keep its context focused too.
- **Brace rule** — in examples, use single braces for JSON structure and double
  braces only for real Jinja variables that reference another node, e.g.
  `{{ trigger_1.data.id }}`. (This markdown is served as text, not templated — over-
  escaping `{{ }}` will render literally.)
- **Keep app-level lean** — per-module fields, examples, and output shapes belong in
  the module's `context.md`, never in the app-level one.
- **Update it with the module** — because `context.md` lives in `v<N>/`, each version
  carries its own; edit it when you change the module and re-`run`/`deploy`.

See the reference module's `modules/create_records/v1/context.md` for a filled
example, and the connector-root `context.md` for the app-level shape.
