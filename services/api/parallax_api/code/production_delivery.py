from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
import re
from typing import Mapping
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..projects.repository import ProjectRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from ..tools.contracts import ToolActionPolicy, ToolCapability, ToolConsequence
from ..tools.providers import (
    ACTION_BRANCH_CREATE,
    ACTION_COMMIT_WRITE,
    ACTION_PREVIEW_CREATE,
    ACTION_PREVIEW_READ,
    ACTION_PULL_REQUEST_CREATE,
    ACTION_PULL_REQUEST_READ,
    ACTION_REPOSITORY_RESOLVE,
    ACTION_SOURCE_FILE_READ,
    ACTION_SOURCE_TREE_READ,
    GITHUB_TOOL,
    VERCEL_TOOL,
    GitHubProviderActions,
    ProviderClientError,
    ProviderProjectBinding,
    VercelPreviewActions,
    VercelPreviewTarget,
)
from ..tools.providers.credentials import (
    GitHubCredentialProvider,
    ProviderCredentialKind,
    ScopedBearerCredential,
    VercelCredentialProvider,
)
from ..tools.providers.github_client import GitHubRestProviderClient
from ..tools.providers.vercel_client import VercelApiTarget, VercelPreviewRestClient
from ..tools.registry import ToolCapabilityRegistry
from .production_source_projection import ProjectedRepositoryLineageBootstrap
from .source_delivery_composition import (
    EngineeringAttemptDeliveryRecordStore,
    OwnerScopedProjectBindingResolver,
    PreviewTargetResolver,
    ScopedProviderInvocationFactory,
    SourceDeliveryComposition,
    VerifiedLineageDelivery,
)


_GITHUB_CONNECTOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_VERCEL_TOKEN_ENV = re.compile(r"^PARALLAX_VERCEL_TOKEN_[A-Z0-9_]{1,96}$")
_ENV_PREVIEW_TARGETS = "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON"
_ENV_OIDC = "VERCEL_OIDC_TOKEN"
_MAX_TARGETS = 64
_GITHUB_API_VERSION = "2026-03-10"
_GITHUB_DELIVERY_PERMISSIONS = ("contents:write", "metadata:read", "pull_requests:write")


class ProductionDeliveryConfigurationError(RuntimeError):
    """Bounded fail-closed production source-delivery configuration error."""


def _repository_identity_key(repository_ref: str) -> str:
    """Use provider semantics for matching without rewriting persisted identity."""

    if not isinstance(repository_ref, str):
        raise ProductionDeliveryConfigurationError("repository identity is invalid")
    if repository_ref.startswith("github:"):
        return f"github:{repository_ref.removeprefix('github:').casefold()}"
    return repository_ref


class VercelConnectGitHubCredentialProvider(GitHubCredentialProvider):
    """Exchange Vercel deployment OIDC for a verified repository-scoped GitHub token.

    Generic credential resolution preserves the existing app-token contract.
    Production source delivery opts into an additional token-request restriction
    for exactly one repository and the minimum GitHub permissions already allowed
    by Parallax's typed delivery capability. Bearer material never leaves this
    provider/client boundary and is cached only for the request composition.
    """

    def __init__(
        self,
        connector: str,
        *,
        oidc_token: str | None = None,
        request_delivery_permissions: bool = False,
        transport: httpx.BaseTransport | None = None,
        github_transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not isinstance(connector, str) or not _GITHUB_CONNECTOR.fullmatch(connector):
            raise ProductionDeliveryConfigurationError("GitHub Connect connector configuration is invalid")
        if not isinstance(request_delivery_permissions, bool):
            raise TypeError("request_delivery_permissions must be bool")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 30:
            raise ValueError("GitHub Connect timeout must be between 0 and 30 seconds")
        timeout = httpx.Timeout(float(timeout_seconds))
        self._connector = connector
        self._oidc_token = oidc_token
        self._request_delivery_permissions = request_delivery_permissions
        self._http = httpx.Client(
            base_url="https://api.vercel.com",
            transport=transport,
            timeout=timeout,
            follow_redirects=False,
        )
        self._github = httpx.Client(
            base_url="https://api.github.com",
            transport=github_transport,
            timeout=timeout,
            follow_redirects=False,
        )
        self._cached: dict[str, ScopedBearerCredential] = {}

    @staticmethod
    def _expiration(value: object) -> datetime:
        try:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                timestamp = float(value)
                if timestamp > 10_000_000_000:
                    timestamp /= 1000.0
                result = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(value, str) and value:
                result = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if result.tzinfo is None:
                    raise ValueError
                result = result.astimezone(timezone.utc)
            else:
                raise ValueError
        except (OverflowError, OSError, TypeError, ValueError) as exc:
            raise ProviderClientError("CREDENTIAL_INVALID") from exc
        if result <= datetime.now(timezone.utc) + timedelta(seconds=30):
            raise ProviderClientError("CREDENTIAL_EXPIRED")
        return result

    @staticmethod
    def _github_repository(repository_ref: str) -> str:
        if not isinstance(repository_ref, str) or not repository_ref.startswith("github:"):
            raise ProviderClientError("CREDENTIAL_SCOPE_MISMATCH")
        repository = repository_ref.removeprefix("github:")
        parts = repository.split("/")
        if len(parts) != 2 or not all(parts):
            raise ProviderClientError("CREDENTIAL_SCOPE_MISMATCH")
        return repository

    @staticmethod
    def delivery_authorization_details(repository: str) -> list[dict[str, object]]:
        return [
            {
                "type": "github_app_installation",
                "repositories": [repository],
                "permissions": list(_GITHUB_DELIVERY_PERMISSIONS),
            }
        ]

    def _verify_repository_scope(self, *, token: str, repository: str) -> None:
        try:
            response = self._github.get(
                "/installation/repositories",
                params={"per_page": 2},
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": _GITHUB_API_VERSION,
                },
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise ProviderClientError("CREDENTIAL_SCOPE_UNVERIFIED") from exc
        if response.status_code != 200:
            raise ProviderClientError("CREDENTIAL_SCOPE_UNVERIFIED")
        try:
            payload = response.json()
        except Exception as exc:
            raise ProviderClientError("CREDENTIAL_SCOPE_UNVERIFIED") from exc
        if not isinstance(payload, dict):
            raise ProviderClientError("CREDENTIAL_SCOPE_UNVERIFIED")
        total_count = payload.get("total_count")
        repositories = payload.get("repositories")
        if total_count != 1 or not isinstance(repositories, list) or len(repositories) != 1:
            raise ProviderClientError("CREDENTIAL_SCOPE_MISMATCH")
        item = repositories[0]
        full_name = item.get("full_name") if isinstance(item, dict) else None
        if not isinstance(full_name, str) or full_name.casefold() != repository.casefold():
            raise ProviderClientError("CREDENTIAL_SCOPE_MISMATCH")

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
            request_payload["authorizationDetails"] = self.delivery_authorization_details(repository)
        try:
            response = self._http.post(
                f"/v1/connect/token/{quote(self._connector, safe='')}",
                headers={"Authorization": f"Bearer {oidc.strip()}", "Content-Type": "application/json"},
                json=request_payload,
            )
        except httpx.TimeoutException as exc:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from exc
        except httpx.RequestError as exc:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from exc
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


class EnvironmentVercelCredentialProvider(VercelCredentialProvider):
    """Expose one server-owned Vercel project-scoped token through #70's type."""

    def __init__(self, secret: str, *, allowed_targets: frozenset[str]) -> None:
        if not isinstance(secret, str) or not secret.strip():
            raise ProductionDeliveryConfigurationError("Vercel scoped credential configuration is unavailable")
        if not allowed_targets:
            raise ProductionDeliveryConfigurationError("Vercel Preview target registry is empty")
        self._secret = secret.strip()
        self._allowed_targets = allowed_targets

    def credential_for_project(self, vercel_project_ref: str) -> ScopedBearerCredential:
        if vercel_project_ref not in self._allowed_targets:
            raise ProviderClientError("CREDENTIAL_SCOPE_MISMATCH")
        return ScopedBearerCredential(
            provider="vercel",
            resource_ref=vercel_project_ref,
            kind=ProviderCredentialKind.VERCEL_SCOPED,
            secret=self._secret,
            expires_at=None,
        )


@dataclass(frozen=True, slots=True)
class RegisteredProductionDeliveryTarget:
    """Server-owned target metadata plus references to its dedicated credentials."""

    api_target: VercelApiTarget
    github_connector: str
    vercel_token_env: str

    def __post_init__(self) -> None:
        if not isinstance(self.api_target, VercelApiTarget):
            raise TypeError("registered Preview target requires a VercelApiTarget")
        if not isinstance(self.github_connector, str) or not _GITHUB_CONNECTOR.fullmatch(self.github_connector):
            raise ValueError("registered GitHub Connect connector is invalid")
        if not isinstance(self.vercel_token_env, str) or not _VERCEL_TOKEN_ENV.fullmatch(self.vercel_token_env):
            raise ValueError("registered Vercel credential reference is invalid")


class RepositoryPreviewTargetResolver(PreviewTargetResolver):
    """Bind a canonical Project to an exact server-registered repository target."""

    def __init__(self, targets: tuple[RegisteredProductionDeliveryTarget, ...]) -> None:
        if not targets or len(targets) > _MAX_TARGETS:
            raise ProductionDeliveryConfigurationError("Vercel Preview target registry is empty or unbounded")
        by_repository: dict[str, RegisteredProductionDeliveryTarget] = {}
        by_ref: dict[str, VercelApiTarget] = {}
        for registration in targets:
            if not isinstance(registration, RegisteredProductionDeliveryTarget):
                raise ProductionDeliveryConfigurationError("Vercel Preview target registry contains an invalid registration")
            target = registration.api_target
            repository_key = _repository_identity_key(target.repository_ref)
            if repository_key in by_repository:
                raise ProductionDeliveryConfigurationError("duplicate repository Preview target registration")
            if target.vercel_project_ref in by_ref:
                raise ProductionDeliveryConfigurationError("duplicate Vercel Preview target registration")
            by_repository[repository_key] = registration
            by_ref[target.vercel_project_ref] = target
        self._by_repository = by_repository
        self.api_targets: Mapping[str, VercelApiTarget] = by_ref

    def registration(self, binding: ProviderProjectBinding) -> RegisteredProductionDeliveryTarget:
        registration = self._by_repository.get(_repository_identity_key(binding.repository_ref))
        if registration is None:
            raise ProductionDeliveryConfigurationError("canonical Project repository has no registered Vercel Preview target")
        return registration

    def resolve(self, binding: ProviderProjectBinding) -> VercelPreviewTarget:
        target = self.registration(binding).api_target
        return VercelPreviewTarget(
            project_ref=binding.project_ref,
            repository_ref=binding.repository_ref,
            vercel_project_ref=target.vercel_project_ref,
        )

    @classmethod
    def from_environment(cls, raw: str | None = None) -> RepositoryPreviewTargetResolver:
        encoded = raw if raw is not None else os.getenv(_ENV_PREVIEW_TARGETS)
        if not isinstance(encoded, str) or not encoded.strip():
            raise ProductionDeliveryConfigurationError("Vercel Preview target registry configuration is unavailable")
        try:
            payload = json.loads(encoded)
        except json.JSONDecodeError as exc:
            raise ProductionDeliveryConfigurationError("Vercel Preview target registry configuration is invalid") from exc
        if not isinstance(payload, list) or not 1 <= len(payload) <= _MAX_TARGETS:
            raise ProductionDeliveryConfigurationError("Vercel Preview target registry must be a bounded non-empty list")
        targets: list[RegisteredProductionDeliveryTarget] = []
        try:
            for item in payload:
                if not isinstance(item, dict):
                    raise ValueError
                api_target = VercelApiTarget(
                    vercel_project_ref=item["vercel_project_ref"],
                    project_id=item["project_id"],
                    project_name=item["project_name"],
                    team_id=item.get("team_id"),
                    repository_ref=item["repository_ref"],
                    github_repo_id=item["github_repo_id"],
                    production_branch=item["production_branch"],
                )
                targets.append(
                    RegisteredProductionDeliveryTarget(
                        api_target=api_target,
                        github_connector=item["github_connector"],
                        vercel_token_env=item["vercel_token_env"],
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductionDeliveryConfigurationError("Vercel Preview target registry contains an invalid target") from exc
        return cls(tuple(targets))


def _project_registry(project_id: str) -> tuple[ToolCapabilityRegistry, str, str]:
    github_capability_id = f"cap:github-delivery:{project_id}"
    vercel_capability_id = f"cap:vercel-preview:{project_id}"
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                capability_id=github_capability_id,
                project_ref=project_id,
                tool=GITHUB_TOOL,
                actions=(
                    ToolActionPolicy(ACTION_REPOSITORY_RESOLVE, ToolConsequence.READ),
                    ToolActionPolicy(ACTION_SOURCE_TREE_READ, ToolConsequence.READ),
                    ToolActionPolicy(ACTION_SOURCE_FILE_READ, ToolConsequence.READ),
                    ToolActionPolicy(ACTION_BRANCH_CREATE, ToolConsequence.MUTATE),
                    ToolActionPolicy(ACTION_COMMIT_WRITE, ToolConsequence.MUTATE),
                    ToolActionPolicy(ACTION_PULL_REQUEST_CREATE, ToolConsequence.MUTATE),
                    ToolActionPolicy(ACTION_PULL_REQUEST_READ, ToolConsequence.READ),
                ),
            ),
            ToolCapability(
                capability_id=vercel_capability_id,
                project_ref=project_id,
                tool=VERCEL_TOOL,
                actions=(
                    ToolActionPolicy(ACTION_PREVIEW_CREATE, ToolConsequence.MUTATE),
                    ToolActionPolicy(ACTION_PREVIEW_READ, ToolConsequence.READ),
                ),
            ),
        )
    )
    return registry, github_capability_id, vercel_capability_id


def production_source_delivery(
    session: Session,
    *,
    owner_subject: str,
    allocator: object,
    project_id: str,
    preview_targets_json: str | None = None,
    environment: Mapping[str, str] | None = None,
    oidc_token: str | None = None,
    github_transport: httpx.BaseTransport | None = None,
    github_scope_transport: httpx.BaseTransport | None = None,
    vercel_transport: httpx.BaseTransport | None = None,
) -> SourceDeliveryComposition:
    """Build the exact accepted #79 delivery stack for one canonical Project."""

    if not isinstance(owner_subject, str) or not owner_subject.strip():
        raise ProductionDeliveryConfigurationError("owner-scoped production delivery requires an authenticated subject")
    project_repository = ProjectRepository(session)
    project = project_repository.get_for_owner(project_id, owner_subject.strip())
    if project is None or project.status != "active":
        raise ProductionDeliveryConfigurationError("canonical owner-scoped Project is unavailable")
    if not project.repository_ref or not project.repository_ref.startswith("github:"):
        raise ProductionDeliveryConfigurationError("canonical Project requires a GitHub repository binding for Wave 2 delivery")

    target_resolver = RepositoryPreviewTargetResolver.from_environment(preview_targets_json)
    binding = ProviderProjectBinding(project_ref=project.id, repository_ref=project.repository_ref)
    selected = target_resolver.registration(binding)
    selected_target = selected.api_target

    env = os.environ if environment is None else environment
    scoped_vercel_token = env.get(selected.vercel_token_env)
    if not isinstance(scoped_vercel_token, str) or not scoped_vercel_token.strip():
        raise ProductionDeliveryConfigurationError("Vercel scoped credential configuration is unavailable for registered target")

    registry, github_capability_id, vercel_capability_id = _project_registry(project.id)
    invocations = ScopedProviderInvocationFactory(
        github_capability_id=github_capability_id,
        vercel_capability_id=vercel_capability_id,
        actor_ref="actor:parallax-runtime",
    )
    github_credentials = VercelConnectGitHubCredentialProvider(
        selected.github_connector,
        oidc_token=oidc_token,
        request_delivery_permissions=True,
        transport=github_transport,
        github_transport=github_scope_transport,
    )
    vercel_credentials = EnvironmentVercelCredentialProvider(
        scoped_vercel_token,
        allowed_targets=frozenset({selected_target.vercel_project_ref}),
    )
    github = GitHubProviderActions(registry, GitHubRestProviderClient(github_credentials))
    selected_api_targets = {selected_target.vercel_project_ref: selected_target}
    vercel = VercelPreviewActions(
        registry,
        VercelPreviewRestClient(
            vercel_credentials,
            selected_api_targets,
            transport=vercel_transport,
        ),
    )
    projects = OwnerScopedProjectBindingResolver(project_repository, owner_subject=owner_subject.strip())
    records = EngineeringAttemptDeliveryRecordStore(EngineeringRunRepository(session))
    bootstrap = ProjectedRepositoryLineageBootstrap(
        allocator=allocator,
        projects=projects,
        github=github,
        invocations=invocations,
    )
    delivery = VerifiedLineageDelivery(
        allocator=allocator,
        projects=projects,
        preview_targets=target_resolver,
        github=github,
        vercel=vercel,
        invocations=invocations,
        records=records,
    )
    return SourceDeliveryComposition(bootstrap=bootstrap, delivery=delivery)


__all__ = [
    "EnvironmentVercelCredentialProvider",
    "ProductionDeliveryConfigurationError",
    "RegisteredProductionDeliveryTarget",
    "RepositoryPreviewTargetResolver",
    "VercelConnectGitHubCredentialProvider",
    "production_source_delivery",
]
