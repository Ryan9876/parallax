from __future__ import annotations

from dataclasses import dataclass
import hmac

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_session
from .repositories.authorized_users import AuthorizedUserRepository
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

OWNER_REQUIRED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Owner access required",
)


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AccessPrincipal:
    subject: str
    role: str
    auth_method: str


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


def access_principal(
    request: Request,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AccessPrincipal:
    expected = settings.access_token
    if not expected:
        if settings.environment in {"development", "test"}:
            return AccessPrincipal(subject="development", role="owner", auth_method="bearer")
        raise AUTH_FAILURE

    if _bearer_matches(credentials, expected):
        return AccessPrincipal(subject="break-glass", role="owner", auth_method="bearer")

    marker = request.headers.get(SESSION_HEADER_NAME)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if marker != SESSION_HEADER_VALUE:
        raise AUTH_FAILURE

    claims = validate_session_token(session_token, expected)
    if claims is None:
        raise AUTH_FAILURE

    if claims.auth_method == "bearer":
        return AccessPrincipal(
            subject=claims.subject,
            role=claims.role,
            auth_method=claims.auth_method,
        )

    repository = AuthorizedUserRepository(session)
    user = repository.get(claims.subject)
    if (
        user is None
        or user.status != "active"
        or not user.auth_user_id
        or user.role != claims.role
    ):
        raise AUTH_FAILURE

    return AccessPrincipal(
        subject=user.id,
        role=user.role,
        auth_method="google",
    )


def require_access(_: AccessPrincipal = Depends(access_principal)) -> None:
    return None


def require_owner(principal: AccessPrincipal = Depends(access_principal)) -> AccessPrincipal:
    if principal.role != "owner":
        raise OWNER_REQUIRED
    return principal
