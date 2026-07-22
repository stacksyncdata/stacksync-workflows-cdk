"""Shared helpers used by more than one module.

Anything two modules would otherwise duplicate belongs here, so each module
stays thin: gather the inputs, call a helper, return a response.

The pieces most connectors end up with:

    api_client.py           HTTP calls, auth headers, retries, error handling
    field_builders.py       turn the system's field metadata into schema fields
    content_handler.py      build the options for dynamic dropdowns
    payload_transformer.py  map submitted form values into the API's payload

Import them from a module handler with the package path, for example
``from utils.api_client import get_records``.

Create only the files you actually need — there is no required set.
"""
