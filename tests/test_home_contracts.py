from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# These tests exercise the request-building logic without contacting vendor APIs.

def test_lg_configuration_contract(monkeypatch):
    import integrations_lg as lg
    monkeypatch.setattr(lg, "LG_PAT", "pat")
    monkeypatch.setattr(lg, "LG_CLIENT_ID", "client")
    monkeypatch.setattr(lg, "LG_COUNTRY", "IN")
    monkeypatch.setattr(lg, "LG_API_KEY", "key")
    headers = lg._headers()
    assert headers["Authorization"] == "Bearer pat"
    assert headers["x-client-id"] == "client"
    assert headers["x-country"] == "IN"
    assert headers["x-service-phase"] == "OP"
    assert headers["x-api-key"]


def test_smartthings_command_payload(monkeypatch):
    import integrations_smartthings as st
    monkeypatch.setattr(st, "_get_access_token", lambda: "token")
    seen = {}
    def fake_request(method, path, *, json_body=None, retries=2):
        seen.update(method=method, path=path, body=json_body)
        return {"results": [{"id": "x"}]}
    monkeypatch.setattr(st, "_request", fake_request)
    result = st.smartthings_execute("dev", "switch", "on")
    assert seen["body"] == {"commands": [{"component": "main", "capability": "switch", "command": "on", "arguments": []}]}
    assert result["ok"] is True


def test_smartthings_capability_enrichment(monkeypatch):
    import integrations_smartthings as st
    monkeypatch.setattr(st, "smartthings_device", lambda device_id: {"device": {"deviceId": device_id, "profile": {"id": "p1"}}})
    monkeypatch.setattr(st, "smartthings_device_profile", lambda profile_id: {"components": [{"id": "main", "capabilities": [{"id": "switch", "version": 1}]}]})
    monkeypatch.setattr(st, "smartthings_device_status", lambda device_id: {"status": {"components": {"main": {}}}})
    monkeypatch.setattr(st, "smartthings_capability_definition", lambda capability_id, version: {"id": capability_id, "version": version, "commands": {"on": {"name": "on"}, "off": {"name": "off"}}})
    result = st.smartthings_device_controls("dev")
    assert result["controls"][0]["capability"] == "switch"
    assert {x["name"] for x in result["controls"][0]["commands"]} == {"on", "off"}


def test_smartthings_capability_fallback_when_profile_unavailable(monkeypatch):
    import integrations_smartthings as st
    monkeypatch.setattr(st, "smartthings_device", lambda device_id: {"device": {
        "deviceId": device_id,
        "profile": {"id": "p1"},
        "components": [{"id": "main", "capabilities": [
            {"id": "switch", "version": 1},
            {"id": "airConditionerMode", "version": 1},
        ]}],
    }})
    def fail_profile(profile_id):
        raise RuntimeError("profile endpoint unavailable")
    monkeypatch.setattr(st, "smartthings_device_profile", fail_profile)
    monkeypatch.setattr(st, "smartthings_device_status", lambda device_id: {"status": {"components": {"main": {}}}})
    monkeypatch.setattr(st, "smartthings_capability_definition", lambda capability_id, version: {
        "id": capability_id, "version": version,
        "commands": {"on": {"name": "on"}, "off": {"name": "off"}} if capability_id == "switch" else {"setAirConditionerMode": {"name": "setAirConditionerMode", "arguments": [{"name": "mode"}]}}
    })
    result = st.smartthings_device_controls("dev")
    assert result["ok"] is True
    assert result["partial"] is True
    assert {x["capability"] for x in result["controls"]} == {"switch", "airConditionerMode"}
    assert result["errors"][0]["stage"] == "device_profile"
