"""End-to-end wire-contract tests: the exact envelopes the platform consumes."""

from __future__ import annotations

from tests.conftest import credentials_envelope


def test_schema_envelope_is_data_schema(client):
    resp = client.post(
        "/create_records/v1/schema",
        json={"data": {"form_data": {}}, "credentials": credentials_envelope()},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    # Single-emit: schema lives only under data.schema (no duplicate top-level key).
    assert set(body.keys()) == {"data"}
    assert set(body["data"].keys()) == {"schema"}
    schema = body["data"]["schema"]
    assert schema["metadata"]["workflows_module_schema_version"] == "1.0.0"
    assert schema["connections"]["app_types"] == ["generic_api_credentials"]
    assert [f["id"] for f in schema["fields"]] == ["record_type"]


def test_schema_is_dynamic_on_form_data(client):
    resp = client.post(
        "/create_records/v1/schema",
        json={
            "data": {"form_data": {"record_type": "contact"}},
            "credentials": credentials_envelope(),
        },
    )
    fields = [f["id"] for f in resp.get_json()["data"]["schema"]["fields"]]
    assert fields == ["record_type", "status"]


def test_content_envelope_id_data_pagination(client):
    resp = client.post(
        "/create_records/v1/content",
        json={
            "data": {"form_data": {}, "content_object_names": [{"id": "record_type"}]},
            "credentials": credentials_envelope(),
        },
    )
    assert resp.status_code == 200
    objects = resp.get_json()["data"]["content_objects"]
    assert len(objects) == 1
    obj = objects[0]
    assert obj["id"] == "record_type"
    assert obj["content_object_name"] == "record_type"
    assert obj["pagination"] == {"data": {}, "has_next_page": False}
    assert obj["data"][0] == {"value": "contact", "label": "Contact", "index": 0}
    assert obj["data"][1]["index"] == 1


def test_execute_wraps_data_with_metadata_and_data_type(client):
    resp = client.post(
        "/create_records/v1/execute",
        json={"data": {"record_type": "contact"}, "credentials": credentials_envelope()},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["created"] == "contact"
    assert body["data"]["api_key_seen"] == "secret-123"
    assert body["metadata"] == {"affected_records": 1}
    assert body["data_type"] == "record"


def test_execute_managed_error_is_flat(client):
    resp = client.post(
        "/create_records/v1/execute",
        json={"data": {"record_type": "contact"}, "credentials": {}},
    )
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["error"] == "No credentials provided"
    assert "data" not in body or body.get("data") == {}


def test_execute_unhandled_error_is_500_envelope(client):
    resp = client.post(
        "/create_records/v1/execute",
        json={"data": {"record_type": "boom"}, "credentials": credentials_envelope()},
    )
    assert resp.status_code == 500
    body = resp.get_json()
    assert "error" in body
    assert body["status_code"] == 500


def test_app_config_lists_modules(client):
    body = client.get("/app-config").get_json()
    assert body["data"]["app_settings"]["app_type"] == "acme"
    modules = body["data"]["modules"]
    assert len(modules) == 1
    module = modules[0]
    assert module["module_id"] == "acme-create_records-1"
    assert module["module_type"] == "create_records"
    assert module["module_version"] == "1"
    assert module["module_name"] == "Create Records"
    assert module["supports_action"] is True
    assert module["supports_trigger"] is False


def test_health(client):
    body = client.get("/health").get_json()
    assert body["data"]["status"] == "healthy"
