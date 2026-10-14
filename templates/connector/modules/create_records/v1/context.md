# Create Records

## What it does
Creates one or more records of the chosen object and returns the created records as
`data`, with their count in `metadata.affected_records`. Works for every standard
object and the account's custom objects.
TODO: the API call it makes (method and path) and anything it returns besides the
records.

## When to use it / when not to
- Use when: a workflow needs to create new records.
- Don't use when: the records may already exist (use Upsert Records) or must be
  changed (use Update Records).

## Connection
TODO: the connection type and the keys this module reads, e.g. "The app's
generic_api_credentials connection; `api_credentials` holds the API token."

## Inputs
- `select_object` (required, string): the object to create. Its options come from
  `/content` and list every standard object and the account's custom objects.
  Choosing one reloads the form with that object's fields.
- `<object>s` (required, array): the records to create, one item per record, each
  keyed by the chosen object's fields.
TODO: the fields of the main objects that are required or need a specific format
(dates, ids, picklist values).

## Output
`data` is the list of created records, in the order they were sent.
TODO: the fields each created record has (at least its id).

## Limits & errors
TODO: the API's real limits and the EXACT error message you raise for each, e.g.
"At most 100 records per run -> 'Maximum 100 records per request' -> split the
input upstream."

## Prerequisites & order
<!-- Optional: ordering rules, e.g. "the parent company must exist before a contact
     is linked to it". Delete this section if none. -->

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
      "reason": "The object to create; choosing it reloads the form with the contact fields.",
      "summary": "Object"
    },
    {
      "field_id": "contacts",
      "field_value": [
        { "name": "Ada Lovelace", "email": "ada@example.com" }
      ],
      "reason": "One record, keyed by the contact fields.",
      "summary": "One contact"
    }
  ]
}
```
COMMENTS:
`select_object` -> changing it reloads the records sub-form
`contacts` -> one item per record; take a value from an upstream step with {{ trigger_1.data.name }}

## EXAMPLES end ##

<!-- Brace rule: single braces for JSON structure; double braces ONLY for real
     Jinja variables that reference another step, e.g. {{ trigger_1.data.id }}.
     Deployment is refused while a required section is missing, empty or still has a
     TODO. Check with: python -m stacksync_cdk.connector_checks -->
