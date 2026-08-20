from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import settings


AUTH_FAILURE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"},
)


def require_access(authorization: str | None = Header(default=None)) -> None:
    expected = settings.access_token
    if not expected:
        if settings.environment in {"development", "test"}:
            return
        raise AUTH_FAILURE

    scheme, separator, candidate = (authorization or "").partition(" ")
    if separator != " " or scheme.casefold() != "bearer":
        raise AUTH_FAILURE
    if not hmac.compare_digest(candidate, expected):
        raise AUTH_FAILURE
