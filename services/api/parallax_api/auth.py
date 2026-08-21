from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .session import (
    SESSION_COOKIE_NAME,
    SESSION_HEADER_NAME,
    SESSION_HEADER_VALUE,
    validate_session_token,
)


AUTH_FAILURE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"},
)


bearer_scheme = HTTPBearer(auto_error=False)


def _bearer_matches(
    credentials: HTTPAuthorizationCredentials | None,
    expected: str,
) -> bool:
    return bool(
        credentials
        and credentials.scheme.casefold() == "bearer"
        and hmac.compare_digest(credentials.credentials, expected)
    )


def require_bearer(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    expected = settings.access_token
    if not expected:
        if settings.environment in {"development", "test"}:
            return
        raise AUTH_FAILURE

    if not _bearer_matches(credentials, expected):
        raise AUTH_FAILURE


def require_access(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    expected = settings.access_token
    if not expected:
        if settings.environment in {"development", "test"}:
            return
        raise AUTH_FAILURE

    if _bearer_matches(credentials, expected):
        return

    marker = request.headers.get(SESSION_HEADER_NAME)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if (
        marker == SESSION_HEADER_VALUE
        and validate_session_token(session_token, expected)
    ):
        return

    raise AUTH_FAILURE
