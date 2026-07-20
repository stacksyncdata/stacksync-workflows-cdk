"""Unit tests for the typed primitives (no Flask app)."""

from __future__ import annotations

import pytest

from stacksync_cdk import (
    ContentResponse,
    Credentials,
    ExecuteResponse,
    Request,
    SchemaResponse,
    validate_array,
    validate_object,
)


def test_request_execute_reads_top_level_data_and_credentials():
    req = Request(
        {
            "data": {"record_type": "contact"},
            "credentials": {"connection_data": {"value": {"api_key": "k"}}},
        }
    )
    assert req.data == {"record_type": "contact"}
    assert req.credentials.api_key == "k"


def test_request_content_object_names_normalized():
    req = Request({"data": {"content_object_names": [{"id": "a"}, "b"]}})
    assert req.content_object_names == ["a", "b"]


def test_credentials_from_inline_connection_field():
    # Style-1: connection delivered inside data[<field>], not top-level.
    payload = {"data": {"pg_conn": {"connection_data": {"value": {"connection_string": "dsn"}}}}}
    creds = Credentials.from_payload(payload)
    assert creds.connection_string == "dsn"


def test_credentials_oauth_accessors_and_no_refresh_token():
    creds = Credentials(
        {
            "connection_data": {
                "value": {
                    "access_token": "tok",
                    "instance_url": "https://x",
                },
                "connection_app_type": "salesforce",
            }
        }
    )
    assert creds.access_token == "tok"
    assert creds.token_type == "Bearer"
    assert creds.get("instance_url") == "https://x"  # provider context via .get()
    assert creds.connection_app_type == "salesforce"


def test_credentials_empty_is_falsy():
    assert not Credentials(None)
    assert not Credentials({})


def test_schema_response_defaults_metadata_and_fields():
    schema = SchemaResponse([{"id": "a", "type": "string"}]).to_schema_dict()
    assert schema["metadata"]["workflows_module_schema_version"] == "1.0.0"
    assert schema["fields"] == [{"id": "a", "type": "string"}]
    # Insertion order: metadata precedes fields.
    assert list(schema.keys())[0] == "metadata"


def test_schema_response_from_schema_preserves_dict():
    raw = {"metadata": {"workflows_module_schema_version": "2.0.0"}, "fields": [], "custom": 1}
    assert SchemaResponse.from_schema(raw).to_schema_dict()["custom"] == 1


def test_schema_response_add_record_array_wraps_and_preserves_base():
    base = {
        "metadata": {"workflows_module_schema_version": "1.0.0"},
        "connections": {"required": True, "app_types": ["generic_api_credentials"]},
        "fields": [{"id": "select_object", "type": "string"}],
    }
    schema = (
        SchemaResponse.from_schema(base)
        .add_record_array("customer", [{"id": "name", "type": "string"}])
        .to_schema_dict()
    )
    assert [f["id"] for f in schema["fields"]] == ["select_object", "customers"]
    array = schema["fields"][1]
    assert array["type"] == "array"
    assert array["validation"] == {"required": True, "min_items": 1}
    assert array["items"]["fields"][0]["id"] == "name"
    assert array["items"]["ui_options"]["ui_order"] == ["name"]
    # BASE must not be mutated across calls.
    assert [f["id"] for f in base["fields"]] == ["select_object"]


def test_content_response_constructor_assigns_index():
    wire = ContentResponse({"objs": [{"value": 1, "label": "one"}]}).to_wire()
    obj = wire["content_objects"][0]
    # Both envelope keys (primary populate reads id; update-refresh reads content_object_name).
    assert obj["id"] == "objs"
    assert obj["content_object_name"] == "objs"
    assert obj["data"][0] == {"value": 1, "label": "one", "index": 0}
    assert obj["pagination"] == {"data": {}, "has_next_page": False}


def test_content_response_add_supports_pagination():
    wire = (
        ContentResponse().add("objs", [{"value": 1, "label": "one"}], has_next_page=True).to_wire()
    )
    assert wire["content_objects"][0]["pagination"]["has_next_page"] is True


def test_execute_response_omits_absent_metadata_and_data_type():
    assert ExecuteResponse({"a": 1}).to_wire() == {"data": {"a": 1}}


def test_validation_rejects_bad_output():
    # content option missing label
    with pytest.raises(ValueError):
        ContentResponse({"objs": [{"value": "x"}]})
    # schema field missing type
    with pytest.raises(ValueError):
        SchemaResponse([{"id": "a"}])
    # connections missing app_types
    with pytest.raises(ValueError):
        SchemaResponse([], connections={"required": True})
    # execute metadata must be a dict
    with pytest.raises(TypeError):
        ExecuteResponse({"a": 1}, metadata="nope")  # pyright: ignore[reportArgumentType]


def test_validation_allows_extra_keys_and_custom_widgets():
    # A custom widget / extra field keys must NOT be rejected.
    schema = SchemaResponse(
        [{"id": "code", "type": "string", "ui_options": {"ui_widget": "CodeblockWidget"}}]
    ).to_schema_dict()
    assert schema["fields"][0]["ui_options"]["ui_widget"] == "CodeblockWidget"
    # An option with a preview + extra key survives.
    wire = ContentResponse({"o": [{"value": 1, "label": "one", "preview": "p", "x": 9}]}).to_wire()
    row = wire["content_objects"][0]["data"][0]
    assert row["preview"] == "p" and row["x"] == 9


def test_validators():
    assert validate_array("[1,2]", "f") == [1, 2]
    assert validate_object('{"a":1}', "f") == {"a": 1}
    with pytest.raises(ValueError):
        validate_array("{}", "f")
