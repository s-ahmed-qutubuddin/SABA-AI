from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from config import (
    IR_BACKEND, IR_BASE_URL, IR_CONTROL_PATH, IR_STATUS_PATH, IR_DEVICE_ID,
    IR_DEVICE_NAME, IR_HTTP_TIMEOUT_SECONDS, IR_HTTP_TOKEN, IR_DEVICES_FILE,
    IR_COMMANDS_FILE,
)

IR_HTTP_TIMEOUT = IR_HTTP_TIMEOUT_SECONDS


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def _device_config() -> list[dict[str, Any]]:
    items = _read_json(IR_DEVICES_FILE, [])
    if isinstance(items, dict):
        items = items.get("devices", [])
    return items if isinstance(items, list) else []


def _learned_commands() -> dict[str, dict[str, Any]]:
    value = _read_json(IR_COMMANDS_FILE, {})
    if not isinstance(value, dict):
        return {}
    # Backward-compatible normalization: old flat command files remain usable.
    # The current schema uses known remote ids (`ac_1`, `ac_2`, ...); `_global` is
    # also reserved for legacy/global commands.
    remote_ids = {
        str(r.get("id"))
        for d in _device_config()
        for r in _remotes_for_device(d)
        if r.get("id")
    }
    if value and ("_global" in value or any(str(k) in remote_ids for k in value)):
        return value
    return {"_global": value} if value else {}


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if IR_HTTP_TOKEN:
        headers["Authorization"] = f"Bearer {IR_HTTP_TOKEN}"
    return headers


def ir_configured() -> bool:
    if IR_BACKEND not in {"http", "webhook"}:
        return False
    return bool(IR_BASE_URL and IR_DEVICE_ID)


def _configured_devices() -> list[dict[str, Any]]:
    configured = _device_config()
    if configured:
        return configured
    if IR_DEVICE_ID:
        return [{
            "id": IR_DEVICE_ID,
            "name": IR_DEVICE_NAME,
            "type": "infrared_blaster",
            "provider": "ir",
            "online": None,
            "capabilities": ["send_ir", "learn_ir"],
            "remotes": [],
        }]
    return []


def _remotes_for_device(device: dict[str, Any]) -> list[dict[str, Any]]:
    remotes = device.get("remotes") or []
    if not isinstance(remotes, list):
        return []
    return [r for r in remotes if isinstance(r, dict) and r.get("id")]


def ir_provider_health() -> dict[str, Any]:
    commands = _learned_commands()
    return {
        "provider": "ir",
        "backend": IR_BACKEND,
        "configured": ir_configured(),
        "transport": "generic-http",
        "device_id": IR_DEVICE_ID or None,
        "device_name": IR_DEVICE_NAME or None,
        "status_endpoint": bool(IR_STATUS_PATH),
        "remote_slots": sum(len(_remotes_for_device(d)) for d in _configured_devices()),
        "learned_command_slots": sum(len(v) for k, v in commands.items() if k != "_global" and isinstance(v, dict)),
        "note": "Two logical AC remotes are defined locally. Actual command delivery stays disabled until the HomeMate transport is verified.",
    }


def ir_list_devices() -> dict[str, Any]:
    devices = []
    for d in _configured_devices():
        remotes = _remotes_for_device(d)
        devices.append({
            "provider": "ir",
            "id": d.get("id"),
            "name": d.get("name") or d.get("id"),
            "model": d.get("model"),
            "type": d.get("type", "infrared_blaster"),
            "online": d.get("online"),
            "capabilities": d.get("capabilities") or ["send_ir", "learn_ir"],
            "aliases": d.get("aliases") or [],
            "appliances": d.get("appliances") or [r.get("id") for r in remotes],
            "remotes": remotes,
        })
    return {"ok": True, "provider": "ir", "devices": devices}


def ir_find_device(query: str) -> dict[str, Any]:
    q = (query or "").strip().lower()
    matches = []
    for d in ir_list_devices()["devices"]:
        remote_text = " ".join(
            f"{r.get('id', '')} {r.get('name', '')} {' '.join(map(str, r.get('aliases', [])))}"
            for r in d.get("remotes", [])
        )
        hay = " ".join([
            str(d.get("id", "")), str(d.get("name", "")), str(d.get("model", "")),
            str(d.get("type", "")), " ".join(map(str, d.get("aliases", []))),
            " ".join(map(str, d.get("appliances", []))), remote_text,
        ]).lower()
        if q and q in hay:
            matches.append(d)
    return {"ok": True, "provider": "ir", "matches": matches}


def ir_device_status(device_id: str) -> dict[str, Any]:
    if not ir_configured():
        return {"ok": False, "provider": "ir", "device_id": device_id, "configured": False, "error": "IR backend is not configured."}
    if not IR_STATUS_PATH:
        return {
            "ok": True, "provider": "ir", "device_id": device_id, "state": {}, "verified": False,
            "verification_note": "No status endpoint configured; IR command delivery can be confirmed only by the transport response.",
        }
    try:
        response = requests.get(
            f"{IR_BASE_URL}{IR_STATUS_PATH}", headers=_headers(), params={"device_id": device_id}, timeout=IR_HTTP_TIMEOUT
        )
        payload = response.json() if response.content else {}
        if response.status_code >= 400:
            return {"ok": False, "provider": "ir", "device_id": device_id, "error": f"IR status HTTP {response.status_code}: {str(payload)[:800]}"}
        return {"ok": True, "provider": "ir", "device_id": device_id, "state": payload, "verified": True}
    except Exception as exc:
        return {"ok": False, "provider": "ir", "device_id": device_id, "error": str(exc), "verified": False}


def ir_device_capabilities(device_id: str) -> dict[str, Any]:
    for d in ir_list_devices()["devices"]:
        if d.get("id") == device_id:
            return {
                "ok": True,
                "provider": "ir",
                "device_id": device_id,
                "capabilities": d.get("capabilities", []),
                "appliances": d.get("appliances", []),
                "remotes": d.get("remotes", []),
                "learned_commands": _learned_commands(),
            }
    return {"ok": False, "provider": "ir", "device_id": device_id, "error": "IR device is not configured."}


def _remote_id_for(command: dict[str, Any]) -> str | None:
    explicit = str(command.get("remote_id") or "").strip()
    if explicit:
        return explicit
    appliance = str(command.get("appliance") or "").strip().lower()
    if not appliance:
        return None
    for d in ir_list_devices()["devices"]:
        for r in d.get("remotes", []):
            aliases = {str(x).strip().lower() for x in r.get("aliases", [])}
            if appliance == str(r.get("id", "")).lower() or appliance == str(r.get("name", "")).lower() or appliance in aliases:
                return str(r["id"])
    return appliance


def _known_command(remote_id: str | None, name: str) -> dict[str, Any] | None:
    learned = _learned_commands()
    if remote_id and remote_id in learned and isinstance(learned[remote_id], dict):
        value = learned[remote_id].get(name)
        if isinstance(value, dict):
            return value
    global_commands = learned.get("_global", {})
    value = global_commands.get(name) if isinstance(global_commands, dict) else None
    return value if isinstance(value, dict) else None


def _payload(device_id: str, command: dict[str, Any]) -> dict[str, Any]:
    name = str(command.get("command") or command.get("action") or "").strip()
    if not name:
        raise ValueError("IR command requires command or action.")
    remote_id = _remote_id_for(command)
    known = _known_command(remote_id, name)
    payload = {
        "device_id": device_id,
        "remote_id": remote_id,
        "command": name,
        "arguments": command.get("arguments") or [],
    }
    if known:
        payload["learned"] = known
    if "appliance" in command:
        payload["appliance"] = command["appliance"]
    if "raw" in command:
        payload["raw"] = command["raw"]
    return payload


def ir_execute(device_id: str, command: dict[str, Any]) -> dict[str, Any]:
    if not ir_configured():
        return {
            "ok": False,
            "provider": "ir",
            "device_id": device_id,
            "command": command,
            "error": "IR backend is not configured. Your two AC remote slots are ready, but the HomeMate transport must be verified before SABA sends commands.",
        }
    payload = _payload(device_id, command)
    if not payload.get("remote_id"):
        return {"ok": False, "provider": "ir", "device_id": device_id, "command": command, "error": "Specify appliance or remote_id so SABA knows which AC remote to use."}
    if "learned" not in payload and "raw" not in payload:
        return {"ok": False, "provider": "ir", "device_id": device_id, "command": command, "error": f"No learned IR payload exists for remote '{payload['remote_id']}' command '{payload['command']}'. Learn that command first."}
    try:
        response = requests.post(
            f"{IR_BASE_URL}{IR_CONTROL_PATH}", headers=_headers(), json=payload, timeout=IR_HTTP_TIMEOUT
        )
        body = response.json() if response.content else {}
        if response.status_code >= 400:
            return {"ok": False, "provider": "ir", "device_id": device_id, "command": command, "error": f"IR control HTTP {response.status_code}: {str(body)[:1000]}"}
        status = ir_device_status(device_id)
        return {
            "ok": True,
            "provider": "ir",
            "device_id": device_id,
            "command": command,
            "response": body,
            "verified": bool(status.get("verified")),
            "verified_state": status.get("state") if status.get("verified") else None,
            "verification_note": status.get("verification_note"),
        }
    except Exception as exc:
        return {"ok": False, "provider": "ir", "device_id": device_id, "command": command, "error": str(exc)}


def ir_save_learned_command(name: str, payload: dict[str, Any], appliance: str | None = None) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("Command name cannot be empty.")
    commands = _learned_commands()
    remote_id = (appliance or "_global").strip() or "_global"
    bucket = commands.setdefault(remote_id, {})
    if not isinstance(bucket, dict):
        bucket = {}
        commands[remote_id] = bucket
    bucket[name] = payload
    IR_COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = IR_COMMANDS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(commands, indent=2))
    tmp.replace(IR_COMMANDS_FILE)
    return {"ok": True, "remote_id": remote_id, "command": name}
