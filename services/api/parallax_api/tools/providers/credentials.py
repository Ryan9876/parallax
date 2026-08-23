from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Protocol

from .common import ProviderClientError


_RESOURCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


class ProviderCredentialKind(str, Enum):
    GITHUB_APP_INSTALLATION = "GITHUB_APP_INSTALLATION"
    GITHUB_FINE_GRAINED = "GITHUB_FINE_GRAINED"
    VERCEL_OIDC = "VERCEL_OIDC"
    VERCEL_SCOPED = "VERCEL_SCOPED"


class ScopedBearerCredential:
    """Server-internal bearer credential lease with deliberately redacted display."""

    __slots__ = ("provider", "resource_ref", "kind", "expires_at", "__secret")

    def __init__(
        self,
        *,
        provider: str,
        resource_ref: str,
        kind: ProviderCredentialKind,
        secret: str,
        expires_at: datetime | None,
    ) -> None:
        if provider not in {"github", "vercel"}:
            raise ValueError("credential provider must be github or vercel")
        if not isinstance(resource_ref, str) or not _RESOURCE.fullmatch(resource_ref):
            raise ValueError("credential resource identity must be bounded")
        if not isinstance(kind, ProviderCredentialKind):
            raise TypeError("credential kind must be ProviderCredentialKind")
        if not isinstance(secret, str) or secret != secret.strip() or not 8 <= len(secret) <= 8_192:
            raise ValueError("credential bearer material is invalid")
        if any(ord(character) < 0x21 or ord(character) > 0x7E for character in secret):
            raise ValueError("credential bearer material must be printable ASCII without whitespace")
        if expires_at is not None:
            if not isinstance(expires_at, datetime) or expires_at.tzinfo is None:
                raise ValueError("credential expiration must be timezone-aware")
            expires_at = expires_at.astimezone(timezone.utc)

        self.provider = provider
        self.resource_ref = resource_ref
        self.kind = kind
        self.expires_at = expires_at
        self.__secret = secret

    def __repr__(self) -> str:
        expiration = self.expires_at.isoformat() if self.expires_at is not None else None
        return (
            "ScopedBearerCredential("
            f"provider={self.provider!r}, resource_ref={self.resource_ref!r}, "
            f"kind={self.kind.value!r}, expires_at={expiration!r}, secret='<redacted>')"
        )

    __str__ = __repr__

    def authorization_value(self, *, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("credential validation time must be timezone-aware")
        if self.expires_at is not None and self.expires_at <= current.astimezone(timezone.utc):
            raise ProviderClientError("CREDENTIAL_EXPIRED")
        return f"Bearer {self.__secret}"


class GitHubCredentialProvider(Protocol):
    def credential_for_repository(self, repository_ref: str) -> ScopedBearerCredential: ...


class VercelCredentialProvider(Protocol):
    def credential_for_project(self, vercel_project_ref: str) -> ScopedBearerCredential: ...


def require_scoped_credential(
    credential: object,
    *,
    provider: str,
    resource_ref: str,
) -> ScopedBearerCredential:
    if not isinstance(credential, ScopedBearerCredential):
        raise ProviderClientError("CREDENTIAL_UNAVAILABLE")
    if credential.provider != provider or credential.resource_ref != resource_ref:
        raise ProviderClientError("CREDENTIAL_SCOPE_MISMATCH")
    credential.authorization_value()
    return credential
