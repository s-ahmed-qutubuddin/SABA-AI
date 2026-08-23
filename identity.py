from __future__ import annotations

import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from family_profiles import find_or_create_member_user

CREATOR_ACTIVATION_TTL = int(os.getenv("CREATOR_ACTIVATION_TTL_SECONDS", "8"))
CREATOR_SESSION_TTL = int(os.getenv("CREATOR_SESSION_TTL_SECONDS", "1800"))
_CREATOR_SECRET = os.getenv("SABA_CREATOR_ACTIVATION_SECRET", "")
_pending_creator_activation: Optional[dict] = None
_creator_sessions: dict[str, float] = {}


@dataclass(frozen=True)
class Identity:
    user_id: int
    role: str
    source: str
    profile_label: str = "Creator / primary user"
    owner_user_id: int | None = None

    @property
    def is_creator(self) -> bool:
        return self.role in {"creator", "owner"}


def issue_local_creator_activation() -> str:
    global _pending_creator_activation
    nonce = secrets.token_urlsafe(24)
    issued_at = time.monotonic()
    _pending_creator_activation = {"nonce": nonce, "issued_at": issued_at}
    return nonce


def consume_local_creator_activation(nonce: str | None = None) -> bool:
    global _pending_creator_activation
    if not _pending_creator_activation:
        return False

    age = time.monotonic() - float(_pending_creator_activation["issued_at"])
    expected = _pending_creator_activation["nonce"]

    if age > CREATOR_ACTIVATION_TTL:
        _pending_creator_activation = None
        return False

    if nonce is not None and not hmac.compare_digest(expected, nonce):
        return False

    _pending_creator_activation = None
    return True


def issue_creator_session() -> str:
    token = secrets.token_urlsafe(32)
    _creator_sessions[token] = time.monotonic() + CREATOR_SESSION_TTL
    _prune_creator_sessions()
    return token


def consume_creator_session(token: str | None) -> bool:
    if not token:
        return False

    _prune_creator_sessions()
    expiry = _creator_sessions.get(token)
    if expiry is None:
        return False

    if expiry < time.monotonic():
        _creator_sessions.pop(token, None)
        return False

    return True


def _prune_creator_sessions() -> None:
    now = time.monotonic()
    for token, expiry in list(_creator_sessions.items()):
        if expiry < now:
            _creator_sessions.pop(token, None)


def local_creator_activation_secret_configured() -> bool:
    return bool(_CREATOR_SECRET)


def resolve_voice_identity(
    *,
    client_host: str | None,
    activation_hint: str | None = None,
    creator_session_token: str | None = None,
) -> Identity:
    # Creator elevation is limited to loopback clients and either a one-time
    # local clap activation or a short-lived server-issued creator session.
    if client_host in {"127.0.0.1", "::1", "localhost"}:
        if consume_local_creator_activation(activation_hint) or consume_creator_session(creator_session_token):
            return Identity(
                user_id=_default_user_id(),
                role="creator",
                source="local_clap" if activation_hint else "creator_session",
                profile_label="Creator / primary user",
                owner_user_id=_default_user_id(),
            )

    return Identity(
        user_id=_default_user_id(),
        role="primary_user",
        source="default",
        owner_user_id=_default_user_id(),
    )


def identify_family_member(name: str, current_owner_user_id: int) -> Identity:
    profile, member_user_id = find_or_create_member_user(
        name,
        owner_user_id=current_owner_user_id,
    )
    return Identity(
        user_id=member_user_id,
        role="family_member",
        source="voice_identification",
        profile_label=profile["label"],
        owner_user_id=current_owner_user_id,
    )


def _default_user_id() -> int:
    return int(os.getenv("SABA_USER_ID", "1"))
