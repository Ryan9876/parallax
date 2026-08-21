from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings


AUTH_FAILURE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required",
    headers={"WWW-Authenticate": "Bearer"},
)


bearer_scheme = HTTPBearer(auto_error=False)


def require_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    expected = settings.access_token
    if not expected:
        if settings.environment in {"development", "test"}:
            return
        raise AUTH_FAILURE

    if credentials is None:
        raise AUTH_FAILURE

    if credentials.scheme.casefold() != "bearer":
        raise AUTH_FAILURE

    if not hmac.compare_digest(credentials.credentials, expected):
        raise AUTH_FAILURE
