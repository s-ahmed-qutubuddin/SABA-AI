from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, Response

from config import SABA_ACCESS_CODE, SABA_SESSION_SECRET

SESSION_COOKIE = "saba_session"
GATE_COOKIE = "saba_gate"
SESSION_TTL = int(os.getenv("SABA_SESSION_TTL_SECONDS", str(60 * 60 * 24 * 30)))
GATE_TTL = int(os.getenv("SABA_GATE_TTL_SECONDS", "900"))
SECURE_COOKIES = os.getenv("SABA_SECURE_COOKIES", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@dataclass(frozen=True)
class SessionIdentity:
    user_id: int
    owner_user_id: int
    profile_id: int
    role: str
    label: str
    preferred_name: str | None = None

    @property
def profile_label(self) -> str:
    """Compatibility alias used by the router/tool layer."""
    return self.label

@property
def is_creator(self) -> bool:
    """True for the creator/owner account only."""
    return self.role in {"creator", "owner"}

@property
def is_owner(self) -> bool:
    return self.role == "owner"

def _secret() -> bytes:
    if not SABA_SESSION_SECRET:
        raise RuntimeError("SABA_SESSION_SECRET is not configured")
    return SABA_SESSION_SECRET.encode("utf-8")


def _encode(payload: dict[str, Any], ttl: int) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl

    raw = json.dumps(
        body,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    sig = hmac.new(
        _secret(),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()

    signature = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")

    return f"{encoded}.{signature}"


def _decode(token: str) -> dict[str, Any] | None:
    try:
        encoded, signature = token.split(".", 1)

        expected = hmac.new(
            _secret(),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()

        actual = base64.urlsafe_b64decode(
            signature + "=" * (-len(signature) % 4)
        )

        if not hmac.compare_digest(expected, actual):
            return None

        raw = base64.urlsafe_b64decode(
            encoded + "=" * (-len(encoded) % 4)
        )

        payload = json.loads(raw.decode("utf-8"))

        if int(payload.get("exp", 0)) <= int(time.time()):
            return None

        return payload

    except Exception:
        return None


def family_code_configured() -> bool:
    return bool(SABA_ACCESS_CODE)


def verify_family_code(code: str) -> bool:
    return bool(SABA_ACCESS_CODE) and hmac.compare_digest(
        str(code).strip(),
        SABA_ACCESS_CODE,
    )


def set_gate(response: Response) -> None:
    response.set_cookie(
        GATE_COOKIE,
        _encode({"gate": True}, GATE_TTL),
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        max_age=GATE_TTL,
        path="/",
    )


def has_gate(request: Request) -> bool:
    token = request.cookies.get(GATE_COOKIE, "")
    payload = _decode(token)
    return bool(payload and payload.get("gate") is True)


def issue_session(
    *,
    user_id: int,
    owner_user_id: int,
    profile_id: int,
    role: str,
    label: str,
    preferred_name: str | None,
) -> str:
    return _encode(
        {
            "user_id": int(user_id),
            "owner_user_id": int(owner_user_id),
            "profile_id": int(profile_id),
            "role": role,
            "label": label,
            "preferred_name": preferred_name,
        },
        SESSION_TTL,
    )


def set_session(response: Response, identity: SessionIdentity) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        issue_session(
            user_id=identity.user_id,
            owner_user_id=identity.owner_user_id,
            profile_id=identity.profile_id,
            role=identity.role,
            label=identity.label,
            preferred_name=identity.preferred_name,
        ),
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        max_age=SESSION_TTL,
        path="/",
    )


def clear_auth(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(GATE_COOKIE, path="/")


def identity_from_token(token: str | None) -> SessionIdentity | None:
    if not token:
        return None

    payload = _decode(token)

    if not payload:
        return None

    if "user_id" not in payload or "owner_user_id" not in payload:
        return None

    try:
        return SessionIdentity(
            user_id=int(payload["user_id"]),
            owner_user_id=int(payload["owner_user_id"]),
            profile_id=int(payload["profile_id"]),
            role=str(payload["role"]),
            label=str(payload["label"]),
            preferred_name=payload.get("preferred_name"),
        )
    except (KeyError, TypeError, ValueError):
        return None


def identity_from_request(request: Request) -> SessionIdentity | None:
    return identity_from_token(
        request.cookies.get(SESSION_COOKIE)
    )


def require_identity(request: Request) -> SessionIdentity:
    identity = identity_from_request(request)

    if identity is None:
        raise HTTPException(
            status_code=401,
            detail="SABA session required",
        )

    return identity


def identity_from_cookie_header(
    cookie_header: str | None,
) -> SessionIdentity | None:
    if not cookie_header:
        return None

    for chunk in cookie_header.split(";"):
        name, _, value = chunk.strip().partition("=")

        if name == SESSION_COOKIE:
            return identity_from_token(value)

    return None
