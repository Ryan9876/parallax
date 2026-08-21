from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import time


SESSION_COOKIE_NAME = "parallax_session"
SESSION_HEADER_NAME = "X-Parallax-Session"
SESSION_HEADER_VALUE = "1"
SESSION_TTL_SECONDS = 8 * 60 * 60
_SESSION_VERSION = "v2"


@dataclass(frozen=True)
class SessionClaims:
    subject: str
    role: str
    auth_method: str
    expires_at: int


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def issue_session_token(
    secret: str,
    *,
    subject: str = "break-glass",
    role: str = "owner",
    auth_method: str = "bearer",
    now: int | None = None,
) -> tuple[str, int]:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + SESSION_TTL_SECONDS
    payload = {
        "auth": auth_method,
        "exp": expires_at,
        "role": role,
        "sub": subject,
    }
    encoded_payload = _b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signed_value = f"{_SESSION_VERSION}.{encoded_payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{signed_value}.{signature}", expires_at


def validate_session_token(
    token: str | None,
    secret: str,
    *,
    now: int | None = None,
) -> SessionClaims | None:
    if not token or not secret:
        return None

    try:
        version, encoded_payload, candidate_signature = token.split(".", 2)
    except (TypeError, ValueError):
        return None

    if version != _SESSION_VERSION:
        return None

    signed_value = f"{version}.{encoded_payload}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(candidate_signature, expected_signature):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        subject = str(payload["sub"])
        role = str(payload["role"])
        auth_method = str(payload["auth"])
        expires_at = int(payload["exp"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    if not subject or role not in {"owner", "member"}:
        return None
    if auth_method not in {"google", "bearer"}:
        return None

    current_time = int(time.time() if now is None else now)
    if expires_at <= current_time:
        return None

    return SessionClaims(
        subject=subject,
        role=role,
        auth_method=auth_method,
        expires_at=expires_at,
    )
