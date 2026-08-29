from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from urllib.parse import quote

import httpx

from ..tools.providers import ProviderClientError
from ..tools.providers.credentials import ProviderCredentialKind, ScopedBearerCredential
from .production_delivery import VercelConnectGitHubCredentialProvider


_ENV_OIDC = "VERCEL_OIDC_TOKEN"


class RepositoryAuthorizationAwareGitHubCredentialProvider(
    VercelConnectGitHubCredentialProvider
):
    """Preserve exact Connect scoping while distinguishing missing repo consent.

    Vercel Connect returns HTTP 422 when a syntactically valid exact-repository
    authorization request cannot be satisfied by the connector installation.
    For Parallax's bounded `github_app_installation` request this means the
    Project repository is not currently covered by the approved installation.

    Only that exact 422 case is normalized to
    `REPOSITORY_AUTHORIZATION_REQUIRED`. Network, OIDC, provider availability,
    malformed-response, expiry, and scope-verification failures keep their
    existing fail-closed result codes. A successful token is still accepted only
    after the inherited verifier proves it sees exactly the requested repository.
    """

    def credential_for_repository(self, repository_ref: str) -> ScopedBearerCredential:
        current = self._cached.get(repository_ref)
        if current is not None and current.expires_at is not None:
            if current.expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
                return current

        repository = self._github_repository(repository_ref)
        oidc = self._oidc_token or os.getenv(_ENV_OIDC)
        if not isinstance(oidc, str) or not oidc.strip():
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE")

        request_payload: dict[str, object] = {"subject": {"type": "app"}}
        if self._request_delivery_permissions:
            request_payload["authorizationDetails"] = self.delivery_authorization_details(
                repository
            )

        try:
            response = self._http.post(
                f"/v1/connect/token/{quote(self._connector, safe='')}",
                headers={
                    "Authorization": f"Bearer {oidc.strip()}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
        except httpx.TimeoutException as exc:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from exc
        except httpx.RequestError as exc:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from exc

        if response.status_code == 422 and self._request_delivery_permissions:
            raise ProviderClientError("REPOSITORY_AUTHORIZATION_REQUIRED")
        if not 200 <= response.status_code < 300:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE")

        try:
            payload = response.json()
        except Exception as exc:
            raise ProviderClientError("CREDENTIAL_INVALID") from exc
        if not isinstance(payload, dict):
            raise ProviderClientError("CREDENTIAL_INVALID")

        token = payload.get("token")
        if not isinstance(token, str) or not token.strip():
            raise ProviderClientError("CREDENTIAL_INVALID")
        expires_at = self._expiration(payload.get("expiresAt"))
        secret = token.strip()
        self._verify_repository_scope(token=secret, repository=repository)

        credential = ScopedBearerCredential(
            provider="github",
            resource_ref=repository_ref,
            kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
            secret=secret,
            expires_at=expires_at,
        )
        self._cached[repository_ref] = credential
        return credential


__all__ = ["RepositoryAuthorizationAwareGitHubCredentialProvider"]
