from __future__ import annotations

import os
from typing import Mapping

import httpx

from ..tools.providers import ProviderClientError, ProviderProjectBinding
from .production_bootstrap import VercelConnectGitHubBootstrapCredentialProvider
from .production_delivery import (
    ProductionDeliveryConfigurationError,
    RepositoryPreviewTargetResolver,
)


_RUNTIME_OIDC_HEADER = "x-vercel-oidc-token"
_RUNTIME_OIDC_ENV = "VERCEL_OIDC_TOKEN"
_RUNTIME_READINESS_PROJECT_REF = "00000000-0000-0000-0000-000000000170"
_MAX_BEARER_LENGTH = 8_192


def _runtime_oidc_value(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    token = raw.strip()
    if (
        token == raw
        and 8 <= len(token) <= _MAX_BEARER_LENGTH
        and all(0x21 <= ord(character) <= 0x7E for character in token)
    ):
        return token
    return None


def runtime_vercel_oidc_token(
    headers: Mapping[str, str],
    *,
    environment: str | None = None,
) -> str | None:
    """Resolve server-owned Vercel deployment identity for runtime provider calls.

    A valid request-scoped Vercel token has precedence when present. A present
    but malformed request-scoped token fails closed rather than being replaced
    by another identity source. When that header is absent, production Vercel
    Connect may use the server-injected deployment OIDC token from
    ``VERCEL_OIDC_TOKEN``. No client Authorization header, cookie, query value,
    or application credential participates in this resolution. Non-production
    callers without a valid request token retain the existing no-provider-
    authority behavior and return ``None``.
    """

    raw_request_token = headers.get(_RUNTIME_OIDC_HEADER)
    if raw_request_token is not None:
        request_token = _runtime_oidc_value(raw_request_token)
        if request_token is not None:
            return request_token
        raise ProductionDeliveryConfigurationError("runtime Vercel OIDC credential is malformed")

    runtime_environment = environment if environment is not None else (os.getenv("VERCEL_ENV") or "unknown")
    if runtime_environment == "production":
        environment_token = _runtime_oidc_value(os.getenv(_RUNTIME_OIDC_ENV))
        if environment_token is not None:
            return environment_token
        raise ProductionDeliveryConfigurationError("production runtime Vercel OIDC credential is unavailable")
    return None


def verify_registered_runtime_github_credentials(
    oidc_token: str,
    *,
    preview_targets_json: str | None = None,
    connect_transport: httpx.BaseTransport | None = None,
    github_transport: httpx.BaseTransport | None = None,
) -> int:
    """Verify real runtime Connect exchange and exact registered GitHub scope.

    This preflight is read-only. It reuses the production credential provider so
    readiness cannot diverge from the repository bootstrap credential contract.
    No provider token or response payload is returned or logged.
    """

    if (
        not isinstance(oidc_token, str)
        or oidc_token != oidc_token.strip()
        or not 8 <= len(oidc_token) <= _MAX_BEARER_LENGTH
        or any(ord(character) < 0x21 or ord(character) > 0x7E for character in oidc_token)
    ):
        raise ProviderClientError("CREDENTIAL_UNAVAILABLE")

    targets = RepositoryPreviewTargetResolver.from_environment(preview_targets_json)
    verified = 0
    for target in targets.api_targets.values():
        registration = targets.registration(
            ProviderProjectBinding(
                project_ref=_RUNTIME_READINESS_PROJECT_REF,
                repository_ref=target.repository_ref,
            )
        )
        provider = VercelConnectGitHubBootstrapCredentialProvider(
            registration.github_connector,
            oidc_token=oidc_token,
            request_delivery_permissions=True,
            transport=connect_transport,
            github_transport=github_transport,
        )
        provider.credential_for_repository(target.repository_ref)
        verified += 1
    return verified


__all__ = [
    "runtime_vercel_oidc_token",
    "verify_registered_runtime_github_credentials",
]
