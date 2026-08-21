from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..auth import bearer_scheme, require_access, require_bearer
from ..config import settings
from ..db import get_session
from ..repositories.authorized_users import AuthorizedUserRepository
from ..services.google_identity import IdentityVerificationError, verify_google_identity
from ..session import SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, issue_session_token


router = APIRouter(prefix="/v1/session", tags=["session"])


def _cookie_settings() -> dict[str, object]:
    return {
        "httponly": True,
        "secure": settings.environment == "production",
        "samesite": "lax",
        "path": "/",
    }


def _set_session_cookie(
    response: Response,
    *,
    subject: str,
    role: str,
    auth_method: str,
):
    token, expires_at = issue_session_token(
        settings.access_token,
        subject=subject,
        role=role,
        auth_method=auth_method,
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_TTL_SECONDS,
        **_cookie_settings(),
    )
    return {
        "authenticated": True,
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
    }


@router.post("")
def establish_session(
    response: Response,
    _: None = Depends(require_bearer),
):
    return _set_session_cookie(
        response,
        subject="break-glass",
        role="owner",
        auth_method="bearer",
    )


@router.post("/google")
def establish_google_session(
    response: Response,
    session: Session = Depends(get_session),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
):
    if not credentials or credentials.scheme.casefold() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication required",
        )

    try:
        identity = verify_google_identity(credentials.credentials)
    except IdentityVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication could not be verified",
        ) from exc

    repository = AuthorizedUserRepository(session)
    user = repository.get_by_email(identity.email)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access not granted",
        )

    try:
        user = repository.bind_google_identity(
            user,
            auth_user_id=identity.auth_user_id,
            email=identity.email,
            display_name=identity.display_name,
            avatar_url=identity.avatar_url,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access not granted",
        ) from exc

    return _set_session_cookie(
        response,
        subject=user.id,
        role=user.role,
        auth_method="google",
    )


@router.get("")
def get_session(_: None = Depends(require_access)):
    return {"authenticated": True}


@router.delete("")
def end_session(response: Response):
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=settings.environment == "production",
        httponly=True,
        samesite="lax",
    )
    return {"authenticated": False}
