# <App name>

## What this app is
One paragraph, third person: what system this connector integrates, the API it
wraps (base URL), and how the connection authenticates. Example: "Connects to Acme
CRM via its REST API at https://api.acme.com. A `generic_api_credentials` connection
supplies a bearer token; a 401 means the token has expired and must be reconnected."

## App-wide conventions (ATTENTION)
Things that are true for EVERY module of this app, so they aren't repeated per
module. Example:
- All record ids are prefixed `rec_`.
- Timestamps are ISO-8601 in UTC.

## App-wide limits (IMPORTANT)
Global limits and their errors. Example:
- Every request is capped at 100 records; the API returns 429 with `Retry-After`
  when the rate limit is hit.

<!-- App-level context is the shared preamble the platform's AI prepends to every
     module. Keep it to what's true for ALL modules — per-module fields, examples,
     output shapes, and prerequisites belong in each module's context.md, not here.
     This whole file is optional; delete it if the app has no app-wide notes. -->
