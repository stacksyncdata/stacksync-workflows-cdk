"""Runtime logic for the Create Records module.

Reads the selected object and its array of records, creates them via your API,
and returns the result. The returned ``data`` is what downstream workflow steps
read as ``{{ MODULE.<id>.output }}``. See ../../../guide/execute.md.
"""

from stacksync_cdk import ExecuteResponse, ManagedError, Request


def execute(request: Request) -> ExecuteResponse:
    selected_object = request.data.get("select_object")
    if not selected_object:
        raise ManagedError.validation_error("select_object is required.")

    records = request.data.get(f"{selected_object}s") or []
    if not records:
        raise ManagedError.validation_error(f"At least one {selected_object} is required.")

    # TODO: create each record via your API (use request.credentials.api_key) and
    #       collect what it returns. Batch the calls when your API supports it.
    created: list[dict] = []

    return ExecuteResponse(created, metadata={"affected_records": len(created)})
