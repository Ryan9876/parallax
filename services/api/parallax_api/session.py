from __future__ import annotations

import hashlib
import hmac
import time


SESSION_COOKIE_NAME = "parallax_session"
SESSION_HEADER_NAME = "X-Parallax-Session"
SESSION_HEADER_VALUE = "1"
SESSION_TTL_SECONDS = 8 * 60 * 60
_SESSION_VERSION = "v1"


def issue_session_token(secret: str, *, now: int | None = None) -> tuple[str, int]:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + SESSION_TTL_SECONDS
    payload = f"{_SESSION_VERSION}.{expires_at}"
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}", expires_at


def validate_session_token(token: str | None, secret: str, *, now: int | None = None) -> bool:
    if not token or not secret:
        return False

    try:
        version, expires_text, candidate_signature = token.split(".", 2)
        expires_at = int(expires_text)
    except (TypeError, ValueError):
        return False

    if version != _SESSION_VERSION:
        return False

    current_time = int(time.time() if now is None else now)
    if expires_at <= current_time:
        return False

    payload = f"{version}.{expires_at}"
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(candidate_signature, expected_signature)
