# `context.md` — the module's skill file

`context.md` is how a module explains itself to Stacksync's AI. It is not code and
has no handler: it is one markdown document, served at `/context`, that the platform
processes into the module's **skills** — how the module behaves in a flow, how the
copilot fills its form, and how a genie executes it. A module with a good
`context.md` gets configured and wired correctly by the AI; one without it is used
blind.

Write it well: the quality of this file affects how reliably the AI uses your module
far more than anything else.

## Two levels

- **Module-level** — `modules/<name>/v<N>/context.md`, served at
  `/<name>/v<N>/context`. Describes that one module version. This is where almost
  all content goes.
- **App-level** — `context.md` at the connector root, served at `/context`.
  Optional. Only the things true for **every** module (auth model, app-wide limits
  and conventions). The platform prepends it to each module.

Both are served raw; a missing file returns `404` (a known, graceful state — the AI
simply has no skill for that module).

## What to provide

Describe the module the way you'd describe a tool to a capable colleague who has
never seen your code — in the third person, concretely. Cover:

| Section | What goes in it |
|---|---|
| **What it does** | The task it performs, the API operation, the connection it needs, and **what it returns and in what shape**. |
| **When to use it / when not to** | The scenarios it's the right choice for — and explicit cases where a different module fits. |
| **Inputs** | One line per field: id, required/optional, type, allowed values / exact encoding, and any gotcha. |
| **Limits & errors** | Hard limits, the **exact** error string raised, and how to avoid it. |
| **Prerequisites & order** | Sequencing rules, e.g. "confirm the vendor exists before creating a bill." |
| **Examples** | Concrete, correctly-filled inputs — the highest-signal part. See the format below. |

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
