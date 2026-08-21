from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal, require_owner
from ..db import get_session
from ..repositories.authorized_users import AuthorizedUserRepository
from ..schemas import AuthorizedUserCreate, AuthorizedUserRead, AuthorizedUserStatusUpdate


router = APIRouter(prefix="/v1/access", tags=["access"])


def _read_user(user, *, auth_method: str | None = None) -> AuthorizedUserRead:
    return AuthorizedUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        role=user.role,
        status=user.status,
        auth_method=auth_method,
        bound=bool(user.auth_user_id),
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


@router.get("/me", response_model=AuthorizedUserRead)
def get_me(
    principal: AccessPrincipal = Depends(access_principal),
    session: Session = Depends(get_session),
):
    if principal.auth_method == "bearer":
        return AuthorizedUserRead(
            id=principal.subject,
            email=None,
            display_name="Break-glass access",
            avatar_url=None,
            role="owner",
            status="active",
            auth_method="bearer",
            bound=False,
        )

    user = AuthorizedUserRepository(session).get(principal.subject)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return _read_user(user, auth_method="google")


@router.get("/users", response_model=list[AuthorizedUserRead])
def list_users(
    _: AccessPrincipal = Depends(require_owner),
    session: Session = Depends(get_session),
):
    return [_read_user(user) for user in AuthorizedUserRepository(session).list_all()]


@router.post("/users", response_model=AuthorizedUserRead, status_code=status.HTTP_201_CREATED)
def add_user(
    payload: AuthorizedUserCreate,
    _: AccessPrincipal = Depends(require_owner),
    session: Session = Depends(get_session),
):
    try:
        user = AuthorizedUserRepository(session).add_member(payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _read_user(user)


@router.patch("/users/{user_id}", response_model=AuthorizedUserRead)
def update_user_status(
    user_id: str,
    payload: AuthorizedUserStatusUpdate,
    _: AccessPrincipal = Depends(require_owner),
    session: Session = Depends(get_session),
):
    repository = AuthorizedUserRepository(session)
    user = repository.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authorized user not found")
    try:
        user = repository.set_status(user, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _read_user(user)
