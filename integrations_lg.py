from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from typing import Any, Dict

import requests

LG_PAT = os.getenv("LG_THINQ_PAT", "").strip()
LG_CLIENT_ID = os.getenv("LG_THINQ_CLIENT_ID", "").strip()
LG_COUNTRY = os.getenv("LG_THINQ_COUNTRY", "IN").strip().upper()
LG_LANGUAGE = os.getenv("LG_THINQ_LANGUAGE", "en-IN").strip()
LG_BASE_URL = os.getenv("LG_THINQ_BASE_URL", "https://api-eic.lgthinq.com").rstrip("/")
LG_TIMEOUT = float(os.getenv("LG_THINQ_TIMEOUT_SECONDS", "12"))
# Public API key used by the current ThinQ Connect Python SDK. Keep overrideable so
# the project can follow a future vendor-issued key without code changes.
LG_API_KEY = os.getenv("LG_THINQ_API_KEY", "").strip()
LG_SERVICE_PHASE = os.getenv("LG_THINQ_SERVICE_PHASE", "OP").strip() or "OP"


def configured() -> bool:
    return bool(LG_PAT and LG_CLIENT_ID and LG_COUNTRY)


def _message_id() -> str:
    # ThinQ expects a compact URL-safe id. Match the current SDK's UUID-bytes pattern.
    return base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2].decode("utf-8")


def _headers(extra: Dict[str, str] | None = None) -> Dict[str, str]:
    if not LG_PAT:
        raise RuntimeError("LG ThinQ is not configured: LG_THINQ_PAT is missing.")
    if not LG_CLIENT_ID:
        raise RuntimeError("LG ThinQ is not configured: LG_THINQ_CLIENT_ID is missing.")
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {LG_PAT}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-country": LG_COUNTRY,
        "x-message-id": _message_id(),
        "x-client-id": LG_CLIENT_ID,
        "x-api-key": LG_API_KEY,
        "x-service-phase": LG_SERVICE_PHASE,
    }
    if LG_LANGUAGE:
        headers["x-language"] = LG_LANGUAGE
    if extra:
        headers.update(extra)
    return headers


def _request(method: str, path: str, *, json_body: Any | None = None, timeout: float | None = None) -> Any:
    response = requests.request(
        method,
        f"{LG_BASE_URL}{path}",
        headers=_headers(),
        json=json_body,
        timeout=timeout or LG_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"message": response.text}
    if response.status_code >= 400:
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            code = error.get("code", response.status_code)
            message = error.get("message", response.text[:1000])
            raise RuntimeError(f"LG ThinQ API {code}: {message}")
        raise RuntimeError(f"LG ThinQ API {response.status_code}: {response.text[:1200]}")
    return payload.get("response", payload) if isinstance(payload, dict) else payload


def lg_list_devices() -> dict:
    devices = _request("GET", "/devices") or []
    return {"ok": True, "provider": "lg_thinq", "devices": devices}


def lg_device_profile(device_id: str) -> dict:
    return {"ok": True, "provider": "lg_thinq", "device_id": device_id, "profile": _request("GET", f"/devices/{device_id}/profile") or {}}


def lg_device_state(device_id: str) -> dict:
    return {"ok": True, "provider": "lg_thinq", "device_id": device_id, "state": _request("GET", f"/devices/{device_id}/state") or {}}


def lg_control_device(device_id: str, payload: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("LG ThinQ control payload cannot be empty.")
    response = _request(
        "POST",
        f"/devices/{device_id}/control",
        json_body=payload,
        timeout=max(LG_TIMEOUT, 20),
    )
    return {"ok": True, "provider": "lg_thinq", "device_id": device_id, "response": response}


def lg_device_energy_profile(device_id: str) -> dict:
    return {"ok": True, "provider": "lg_thinq", "device_id": device_id, "profile": _request("GET", f"/devices/energy/{device_id}/profile") or {}}


def lg_device_energy_usage(device_id: str, energy_property: str, period: str, start_date: str, end_date: str) -> dict:
    params = (
        f"property={requests.utils.quote(energy_property, safe='')}"
        f"&period={requests.utils.quote(period, safe='')}"
        f"&startDate={requests.utils.quote(start_date, safe='')}"
        f"&endDate={requests.utils.quote(end_date, safe='')}"
    )
    return {
        "ok": True,
        "provider": "lg_thinq",
        "device_id": device_id,
        "usage": _request("GET", f"/devices/energy/{device_id}/usage?{params}") or {},
    }


def lg_find_device(query: str) -> dict:
    devices = lg_list_devices()["devices"]
    q = (query or "").strip().lower()
    matches = []
    for device in devices:
        info = device.get("deviceInfo") or {}
        hay = " ".join(
            str(info.get(k, ""))
            for k in ("alias", "modelName", "deviceType", "deviceTypeName", "serialNumber")
        ).lower()
        hay += " " + str(device.get("deviceId", "")).lower()
        if q and q in hay:
            matches.append(device)
    return {"ok": True, "provider": "lg_thinq", "matches": matches}
