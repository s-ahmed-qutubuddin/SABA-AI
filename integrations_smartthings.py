from __future__ import annotations

import base64
import json
import os
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import requests

ST_BASE_URL = os.getenv("SMARTTHINGS_BASE_URL", "https://api.smartthings.com/v1").rstrip("/")
ST_APP_ID = os.getenv("SMARTTHINGS_APP_ID", "").strip()
ST_ACCESS_TOKEN = os.getenv("SMARTTHINGS_ACCESS_TOKEN", "").strip()
ST_REFRESH_TOKEN = os.getenv("SMARTTHINGS_REFRESH_TOKEN", "").strip()
ST_CLIENT_ID = os.getenv("SMARTTHINGS_CLIENT_ID", "").strip()
ST_CLIENT_SECRET = os.getenv("SMARTTHINGS_CLIENT_SECRET", "").strip()
ST_REDIRECT_URI = os.getenv("SMARTTHINGS_REDIRECT_URI", "").strip()
ST_TOKEN_EXPIRES_AT = float(os.getenv("SMARTTHINGS_TOKEN_EXPIRES_AT", "0") or 0)
ST_TIMEOUT = float(os.getenv("SMARTTHINGS_TIMEOUT_SECONDS", "12"))
ST_TOKEN_FILE = Path(os.getenv("SMARTTHINGS_TOKEN_FILE", os.path.join(os.path.dirname(__file__), ".smartthings_tokens.json")))

_runtime_access_token = ST_ACCESS_TOKEN
_runtime_refresh_token = ST_REFRESH_TOKEN
_runtime_expires_at = ST_TOKEN_EXPIRES_AT
_REFRESH_LOCK = threading.RLock()


def configured() -> bool:
    return bool(_runtime_access_token or (_runtime_refresh_token and ST_CLIENT_ID and ST_CLIENT_SECRET))


def oauth_configured() -> bool:
    return bool(ST_CLIENT_ID and ST_CLIENT_SECRET and ST_REDIRECT_URI)


def _load_token_store() -> None:
    global _runtime_access_token, _runtime_refresh_token, _runtime_expires_at
    # Production-first: persist OAuth tokens in MySQL so Render restarts do not
    # lose the refresh token. Local file storage remains as a fallback.
    try:
        from database import get_connection
        conn = get_connection(); cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT access_token, refresh_token, expires_at FROM smartthings_tokens WHERE token_id=1 LIMIT 1")
            row = cur.fetchone()
            if row:
                _runtime_access_token = row.get("access_token") or _runtime_access_token
                _runtime_refresh_token = row.get("refresh_token") or _runtime_refresh_token
                _runtime_expires_at = float(row.get("expires_at") or _runtime_expires_at or 0)
                return
        finally:
            cur.close(); conn.close()
    except Exception:
        pass
    try:
        if not ST_TOKEN_FILE.exists():
            return
        payload = json.loads(ST_TOKEN_FILE.read_text())
        _runtime_access_token = payload.get("access_token") or _runtime_access_token
        _runtime_refresh_token = payload.get("refresh_token") or _runtime_refresh_token
        _runtime_expires_at = float(payload.get("expires_at") or _runtime_expires_at or 0)
    except Exception:
        pass


def reload_token_store() -> None:
    _load_token_store()


def _save_token_store() -> None:
    # Always attempt DB persistence first. It is durable across Render redeploys.
    try:
        from database import get_connection
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO smartthings_tokens (token_id, access_token, refresh_token, expires_at) VALUES (1,%s,%s,%s) ON DUPLICATE KEY UPDATE access_token=VALUES(access_token), refresh_token=VALUES(refresh_token), expires_at=VALUES(expires_at)",
                (_runtime_access_token, _runtime_refresh_token, _runtime_expires_at),
            )
            conn.commit()
            return
        finally:
            cur.close(); conn.close()
    except Exception:
        pass
    # Local-development fallback. This file is gitignored and never belongs in the deploy ZIP.
    ST_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = ST_TOKEN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"access_token": _runtime_access_token, "refresh_token": _runtime_refresh_token, "expires_at": _runtime_expires_at}))
    os.chmod(tmp, 0o600)
    tmp.replace(ST_TOKEN_FILE)


_load_token_store()


def set_oauth_tokens(payload: dict) -> None:
    global _runtime_access_token, _runtime_refresh_token, _runtime_expires_at
    _runtime_access_token = str(payload.get("access_token") or "")
    _runtime_refresh_token = str(payload.get("refresh_token") or _runtime_refresh_token or "")
    _runtime_expires_at = time.time() + float(payload.get("expires_in", 86400))
    _save_token_store()

def _get_access_token() -> str:
    global _runtime_access_token, _runtime_refresh_token, _runtime_expires_at
    with _REFRESH_LOCK:
        if _runtime_access_token and (_runtime_expires_at <= 0 or time.time() < _runtime_expires_at - 180):
            return _runtime_access_token
        if not (_runtime_refresh_token and ST_CLIENT_ID and ST_CLIENT_SECRET):
            return _runtime_access_token
        basic = base64.b64encode(f"{ST_CLIENT_ID}:{ST_CLIENT_SECRET}".encode()).decode()
        response = requests.post(
            f"{ST_BASE_URL}/oauth/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "refresh_token", "refresh_token": _runtime_refresh_token, "client_id": ST_CLIENT_ID},
            timeout=ST_TIMEOUT,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"SmartThings token refresh failed: {response.status_code} {response.text[:800]}")
        set_oauth_tokens(response.json())
        return _runtime_access_token


def _headers() -> Dict[str, str]:
    token = _get_access_token()
    if not token:
        raise RuntimeError("SmartThings is not configured. Complete OAuth connection or provide an access token.")
    return {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}


def _request(
    method: str,
    path_or_url: str,
    *,
    json_body: dict | None = None,
    retries: int = 2,
) -> Any:
    """
    Execute a SmartThings API request with bounded recovery.

    - Proactively refreshes near expiry through _headers().
    - On one 401/403, refreshes OAuth credentials once and retries.
    - On 429, respects the server reset hint when available.
    - Never loops indefinitely.
    """
    url = (
        path_or_url
        if path_or_url.startswith("http")
        else f"{ST_BASE_URL}{path_or_url}"
    )

    auth_recovered = False

    for attempt in range(retries + 1):
        response = requests.request(
            method,
            url,
            headers=_headers(),
            json=json_body,
            timeout=ST_TIMEOUT,
        )

        # Authorization recovery. A 403 can be returned by the API when the
        # currently cached access token is stale/invalid for the request.
        if (
            response.status_code in (401, 403)
            and not auth_recovered
            and _runtime_refresh_token
            and ST_CLIENT_ID
            and ST_CLIENT_SECRET
        ):
            with _REFRESH_LOCK:
                globals()["_runtime_expires_at"] = 0
                _get_access_token()
            auth_recovered = True
            continue

        if response.status_code == 429 and attempt < retries:
            reset = response.headers.get("x-ratelimit-reset")
            delay = 1.0

            try:
                if reset:
                    delay = max(
                        0.25,
                        min(
                            10.0,
                            float(reset) - time.time(),
                        ),
                    )
            except (TypeError, ValueError):
                pass

            time.sleep(delay)
            continue

        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text}

        if response.status_code >= 400:
            raise RuntimeError(
                f"SmartThings API {response.status_code}: "
                f"{json.dumps(payload)[:1200]}"
            )

        return payload

    raise RuntimeError(
        "SmartThings request failed after bounded retries."
    )

def smartthings_list_devices() -> dict:
    items: list[dict] = []
    next_url = f"{ST_BASE_URL}/devices?max=200"
    seen: set[str] = set()
    while next_url and next_url not in seen:
        seen.add(next_url)
        data = _request("GET", next_url)
        items.extend(data.get("items", []))
        next_url = ((data.get("_links") or {}).get("next") or {}).get("href")
    return {"ok": True, "provider": "smartthings", "devices": items}


def smartthings_device_status(device_id: str, include_health: bool = False) -> dict:
    suffix = "?includeHealth=true" if include_health else ""
    data = _request("GET", f"/devices/{device_id}/status{suffix}")
    return {"ok": True, "provider": "smartthings", "device_id": device_id, "status": data}


def smartthings_device(device_id: str) -> dict:
    return {"ok": True, "provider": "smartthings", "device_id": device_id, "device": _request("GET", f"/devices/{device_id}")}


def smartthings_execute(device_id: str, capability: str, command: str, args: list[Any] | None = None, component: str = "main") -> dict:
    if not capability or not command:
        raise ValueError("SmartThings control requires capability and command")
    body = {"commands": [{"component": component or "main", "capability": capability, "command": command, "arguments": args or []}]}
    data = _request("POST", f"/devices/{device_id}/commands", json_body=body)
    return {"ok": True, "provider": "smartthings", "device_id": device_id, "response": data}



@lru_cache(maxsize=128)
def smartthings_capability_definition(capability_id: str, version: int = 1) -> dict:
    return _request("GET", f"/capabilities/{capability_id}/{version}")


@lru_cache(maxsize=128)
def smartthings_device_profile(profile_id: str) -> dict:
    return _request("GET", f"/deviceprofiles/{profile_id}")


def _command_definitions(definition: dict) -> list[dict]:
    commands = definition.get("commands") or {}
    if isinstance(commands, dict):
        out = []
        for name, spec in commands.items():
            row = {"name": name}
            if isinstance(spec, dict):
                row.update({k: v for k, v in spec.items() if k != "name"})
            out.append(row)
        return out
    if isinstance(commands, list):
        return [dict(x) for x in commands if isinstance(x, dict)]
    return []


def smartthings_device_controls(device_id: str) -> dict:
    """Return capability-aware controls without failing the whole endpoint.

    SmartThings device profiles/capability definitions are supplemental APIs; a user
    token can successfully read a device/status while a profile or individual
    capability definition is unavailable. In that case we fall back to the device's
    embedded component/capability list and return per-capability definition errors.
    """
    device = smartthings_device(device_id)["device"]
    profile_id = ((device.get("profile") or {}).get("id"))
    errors: list[dict] = []

    profile: dict = {}
    if profile_id:
        try:
            profile = smartthings_device_profile(profile_id) or {}
        except Exception as exc:
            errors.append({"stage": "device_profile", "error": str(exc)})

    status = smartthings_device_status(device_id).get("status") or {}
    unavailable = set()
    try:
        raw = status.get("components", {}).get("main", {}).get("samsungce.unavailableCapabilities", {})
        for item in ((raw.get("unavailableCommands") or {}).get("value") or []):
            unavailable.add(str(item))
    except Exception as exc:
        errors.append({"stage": "unavailable_commands", "error": str(exc)})

    components = profile.get("components") or device.get("components") or []
    controls = []
    for component in components:
        component_id = component.get("id") or "main"
        for cap in component.get("capabilities", []) or []:
            cap_id = cap.get("id")
            version = int(cap.get("version") or 1)
            if not cap_id:
                continue
            try:
                definition = smartthings_capability_definition(cap_id, version)
            except Exception as exc:
                definition = {"id": cap_id, "version": version, "commands": {}}
                errors.append({"stage": "capability_definition", "capability": cap_id, "version": version, "error": str(exc)})
            commands = []
            for command in _command_definitions(definition):
                name = command.get("name")
                if not name:
                    continue
                key = f"{cap_id}.{name}"
                commands.append({
                    "name": name,
                    "arguments": command.get("arguments") or command.get("parameters") or [],
                    "available": key not in unavailable,
                })
            controls.append({
                "component": component_id,
                "capability": cap_id,
                "version": version,
                "definition_available": bool(_command_definitions(definition) or definition.get("attributes")),
                "commands": commands,
                "read_only": not any(c.get("available") for c in commands),
            })

    return {
        "ok": True,
        "provider": "smartthings",
        "device_id": device_id,
        "device": device,
        "profile": profile,
        "status": status,
        "unavailable_commands": sorted(unavailable),
        "controls": controls,
        "errors": errors,
        "partial": bool(errors),
    }


def smartthings_find_device(query: str) -> dict:
    q = (query or "").strip().lower()
    devices = smartthings_list_devices()["devices"]
    matches = []
    for d in devices:
        hay = " ".join(str(d.get(k, "")) for k in ("name", "label", "deviceTypeName", "manufacturerName", "deviceModel", "deviceId")).lower()
        if q and q in hay:
            matches.append(d)
    return {"ok": True, "provider": "smartthings", "matches": matches}
