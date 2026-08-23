from __future__ import annotations

import json
from pathlib import Path


def test_ir_disabled_is_truthful(monkeypatch):
    import devices.ir_blaster as ir
    monkeypatch.setattr(ir, "IR_BACKEND", "disabled")
    monkeypatch.setattr(ir, "IR_BASE_URL", "")
    monkeypatch.setattr(ir, "IR_DEVICE_ID", "")
    assert ir.ir_configured() is False
    result = ir.ir_execute("x", {"command": "power_on"})
    assert result["ok"] is False
    assert "not configured" in result["error"].lower()


def test_ir_http_success_requires_2xx(monkeypatch, tmp_path):
    import devices.ir_blaster as ir
    monkeypatch.setattr(ir, "IR_BACKEND", "http")
    monkeypatch.setattr(ir, "IR_BASE_URL", "http://ir")
    monkeypatch.setattr(ir, "IR_DEVICE_ID", "blaster-1")
    monkeypatch.setattr(ir, "IR_CONTROL_PATH", "/control")
    monkeypatch.setattr(ir, "IR_STATUS_PATH", "")
    commands_file = tmp_path / "commands.json"
    commands_file.write_text(json.dumps({"_global": {"ac_living_power_on": {"code": "TEST"}}}))
    monkeypatch.setattr(ir, "IR_COMMANDS_FILE", commands_file)

    class Resp:
        status_code = 200
        content = b'{"accepted": true}'
        def json(self): return {"accepted": True}

    seen = {}
    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["payload"] = kwargs["json"]
        return Resp()
    monkeypatch.setattr(ir.requests, "post", fake_post)
    result = ir.ir_execute("blaster-1", {"command": "ac_living_power_on", "appliance": "living room ac"})
    assert result["ok"] is True
    assert result["verified"] is False
    assert seen["payload"]["command"] == "ac_living_power_on"


def test_ir_list_devices_from_file(tmp_path, monkeypatch):
    import devices.ir_blaster as ir
    device_file = tmp_path / "devices.json"
    device_file.write_text(json.dumps([{"id": "b1", "name": "HomeMate", "aliases": ["ir"]}]))
    monkeypatch.setattr(ir, "IR_BACKEND", "http")
    monkeypatch.setattr(ir, "IR_BASE_URL", "http://ir")
    monkeypatch.setattr(ir, "IR_DEVICE_ID", "")
    monkeypatch.setattr(ir, "IR_DEVICES_FILE", device_file)
    items = ir.ir_list_devices()["devices"]
    assert items[0]["id"] == "b1"


def test_dual_ac_remote_mapping(monkeypatch, tmp_path):
    import devices.ir_blaster as ir
    device_file = tmp_path / "devices.json"
    commands_file = tmp_path / "commands.json"
    device_file.write_text(json.dumps([{
        "id": "home_ir",
        "name": "HomeMate",
        "remotes": [
            {"id": "ac_1", "name": "AC 1 Remote", "aliases": ["first ac"]},
            {"id": "ac_2", "name": "AC 2 Remote", "aliases": ["second ac"]}
        ]
    }]))
    commands_file.write_text(json.dumps({
        "ac_1": {"power_on": {"code": "ONE"}},
        "ac_2": {"power_on": {"code": "TWO"}}
    }))
    monkeypatch.setattr(ir, "IR_BACKEND", "http")
    monkeypatch.setattr(ir, "IR_BASE_URL", "http://ir")
    monkeypatch.setattr(ir, "IR_DEVICE_ID", "home_ir")
    monkeypatch.setattr(ir, "IR_CONTROL_PATH", "/control")
    monkeypatch.setattr(ir, "IR_STATUS_PATH", "")
    monkeypatch.setattr(ir, "IR_DEVICES_FILE", device_file)
    monkeypatch.setattr(ir, "IR_COMMANDS_FILE", commands_file)

    sent = {}

    class Resp:
        status_code = 200
        content = b'{}'

        def json(self):
            return {}

    def fake_post(url, **kwargs):
        sent["payload"] = kwargs["json"]
        return Resp()

    monkeypatch.setattr(ir.requests, "post", fake_post)
    result = ir.ir_execute("home_ir", {"command": "power_on", "appliance": "first ac"})
    assert result["ok"] is True
    assert sent["payload"]["remote_id"] == "ac_1"
    assert sent["payload"]["learned"]["code"] == "ONE"
