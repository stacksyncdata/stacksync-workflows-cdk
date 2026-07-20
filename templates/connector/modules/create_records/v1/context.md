# Create Records

Creates one or more records of a chosen object type via the connector's API. This
is the reference module — copy its shape when adding new capabilities.

## Inputs
- **select_object** (required): the type of record to create. Its options come from
  your object registry via `/content`; choosing one loads that object's fields
  (`on_action.load_schema`).
- **{object}s** (required): an array of records to create, each with the chosen
  object's fields.

## Credentials
Uses a `generic_api_credentials` connection; the API key is read as
`request.credentials.api_key`.

## Output
Returns your API's result for the created records. Downstream steps read it as
`{{ MODULE.<id>.output }}`.
