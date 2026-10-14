# <App name>

## What this app is
TODO: one paragraph, third person: the system this connector integrates and the API
it calls (base URL).
<!-- Example: "Connects to Acme CRM through its REST API at https://api.acme.com." -->

## Connection
TODO: the connection type (connection_app_type in stacksync.yml) and the exact keys
read from it, with what each holds.
<!-- Example: "A generic_api_credentials connection. `api_credentials` holds the API
     token, sent as `Authorization: Bearer <token>`. A 401 means the token expired and
     the connection must be updated." -->

## Objects
TODO: every standard object, how the account's custom objects and custom fields are
listed, and which operations each object supports.
<!-- Example: "Standard objects: contact, company, deal. Custom objects and custom
     fields are listed live from GET /v1/schema and appear in every module's object
     dropdown. Deals cannot be deleted." -->

## App-wide conventions
<!-- Optional. Only what is true for EVERY module, e.g. "All ids are prefixed
     `rec_`" or "Timestamps are ISO-8601 in UTC". Delete this section if none. -->

## App-wide limits
TODO: rate limits, page sizes and anything else true for every module, with the
error each limit produces.
<!-- Example: "100 requests per minute; over it the API returns 429 with
     Retry-After." -->

<!-- This file is the app-level context Stacksync's AI reads with every module.
     Per-module fields, examples and output shapes belong in each module's
     context.md. Deployment is refused while a required section is missing, empty or
     still has a TODO. Check with: python -m stacksync_cdk.connector_checks -->
