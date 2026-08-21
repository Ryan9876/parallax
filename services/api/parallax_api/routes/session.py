from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response

from ..auth import require_access, require_bearer
from ..config import settings
from ..session import SESSION_COOKIE_NAME, SESSION_TTL_SECONDS, issue_session_token


router = APIRouter(prefix="/v1/session", tags=["session"])


def _cookie_settings() -> dict[str, object]:
    production = settings.environment == "production"
    return {
        "httponly": True,
        "secure": production,
        "samesite": "none" if production else "lax",
        "path": "/",
    }


@router.post("")
def establish_session(
    response: Response,
    _: None = Depends(require_bearer),
):
    token, expires_at = issue_session_token(settings.access_token)
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
        samesite="none" if settings.environment == "production" else "lax",
    )
    return {"authenticated": False}
