# Create Records

## What it does
Creates one or more records of a chosen object type via the connector's API and
returns the created records. Requires a `generic_api_credentials` connection. The
user selects an object type first; the form then regenerates with one input per
field of that object. The result is returned as `data` (the created records) plus
`metadata.affected_records`.

## When to use it / when not to
- Use when: a workflow needs to create new records in the target system.
- Don't use when: you need to update or upsert existing records (use the update /
  upsert module), or read records (use the list / get module).

## Inputs
- `connections` (required) -> a managed `generic_api_credentials` connection.
- `select_object` (required, string) -> the object type to create; its options come
  from `/content`, and choosing one reloads the form with that object's fields.
- `<object>s` (required, array) -> the records to create, each keyed by the selected
  object's fields.

## Limits & errors
- Replace with your API's real limits and the EXACT error you raise, e.g.
  "caps at 10 records per request -> 'Maximum 10 records allowed per request' -> batch
  upstream to create more."

## Prerequisites & order
- None for the reference module. Document any ordering rules your API needs here,
  e.g. "confirm the parent record exists before creating a child."

## EXAMPLES start ##

### Create a single record

Create one contact from an upstream trigger.
FORM DATA:
```json
{
  "summary": "Create one contact",
  "changes": [
    {
      "field_id": "select_object",
      "field_value": "contact",
      "reason": "The object type to create; choosing it regenerates the form with one input per contact field.",
      "summary": "Object type"
    },
    {
      "field_id": "contacts",
      "field_value": [
        { "name": "Ada Lovelace", "email": "ada@example.com" }
      ],
      "reason": "One record, keyed by the selected object's fields.",
      "summary": "Single contact"
    }
  ]
}
```
COMMENTS:
`select_object` -> changing it reloads the records sub-form
`contacts` -> array keyed by the selected object's fields; pull a value from an upstream node with {{ trigger_1.data.name }}

## EXAMPLES end ##

<!-- Brace rule: single braces for JSON structure; double braces ONLY for real
     Jinja variables that reference another node, e.g. {{ trigger_1.data.id }}. -->
