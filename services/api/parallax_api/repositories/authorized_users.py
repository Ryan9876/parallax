from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuthorizedUser, utcnow


def normalize_email(value: str) -> str:
    return value.strip().casefold()


class AuthorizedUserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: str) -> AuthorizedUser | None:
        return self.session.get(AuthorizedUser, user_id)

    def get_by_email(self, email: str) -> AuthorizedUser | None:
        normalized = normalize_email(email)
        statement = select(AuthorizedUser).where(AuthorizedUser.normalized_email == normalized)
        return self.session.scalar(statement)

    def get_by_auth_user_id(self, auth_user_id: str) -> AuthorizedUser | None:
        statement = select(AuthorizedUser).where(AuthorizedUser.auth_user_id == auth_user_id)
        return self.session.scalar(statement)

    def list_all(self) -> list[AuthorizedUser]:
        statement = select(AuthorizedUser).order_by(AuthorizedUser.role.asc(), AuthorizedUser.email.asc())
        return list(self.session.scalars(statement).all())

    def add_member(self, email: str) -> AuthorizedUser:
        normalized = normalize_email(email)
        if not normalized or "@" not in normalized:
            raise ValueError("A valid Google email is required")
        existing = self.get_by_email(normalized)
        if existing:
            raise ValueError("That email is already authorized")

        user = AuthorizedUser(
            email=normalized,
            normalized_email=normalized,
            role="member",
            status="active",
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def bind_google_identity(
        self,
        user: AuthorizedUser,
        *,
        auth_user_id: str,
        email: str,
        display_name: str | None,
        avatar_url: str | None,
    ) -> AuthorizedUser:
        normalized = normalize_email(email)
        if user.normalized_email != normalized:
            raise ValueError("Verified identity does not match authorized email")
        if user.auth_user_id and user.auth_user_id != auth_user_id:
            raise ValueError("Authorized email is already bound to a different identity")

        existing_identity = self.get_by_auth_user_id(auth_user_id)
        if existing_identity and existing_identity.id != user.id:
            raise ValueError("Google identity is already bound to another authorized user")

        user.auth_user_id = auth_user_id
        user.email = normalized
        user.display_name = (display_name or "").strip() or user.display_name
        user.avatar_url = (avatar_url or "").strip() or user.avatar_url
        user.last_login_at = utcnow()
        user.updated_at = utcnow()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def set_status(self, user: AuthorizedUser, status: str) -> AuthorizedUser:
        if status not in {"active", "revoked"}:
            raise ValueError("Unsupported authorization status")
        if user.role == "owner" and status != "active":
            raise ValueError("The owner cannot be revoked in v0.10.0")
        user.status = status
        user.updated_at = utcnow()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
