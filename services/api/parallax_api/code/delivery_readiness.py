from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
import re
from typing import Mapping
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..projects.repository import ProjectRepository
from ..tools.contracts import ToolActionPolicy, ToolCapability, ToolConsequence
from ..tools.providers.common import (
    AuthorizedProviderExecutor,
    ProviderActionFailed,
    ProviderClientError,
    ProviderInvocation,
    ProviderProjectBinding,
    safe_provider_call,
)
from ..tools.providers.credentials import require_scoped_credential
from ..tools.providers.vercel_client import VercelApiTarget
from ..tools.registry import ToolCapabilityRegistry
from .production_delivery import (
    EnvironmentVercelCredentialProvider,
    ProductionDeliveryConfigurationError,
    RepositoryPreviewTargetResolver,
    VercelConnectGitHubCredentialProvider,
    production_source_delivery,
)
from .source_delivery_composition import SourceDeliveryComposition


ACTION_PROJECT_ENSURE = "project.ensure"
_ENV_PREVIEW_TARGETS = "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON"
_MAX_PROJECTS = 100
_PROJECT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


@dataclass(frozen=True, slots=True)
class DeliveryProvisioningProfile:
    team_id: str
    github_connector: str
    vercel_token_env: str


@dataclass(frozen=True, slots=True)
class VerifiedGitHubRepositoryIdentity:
    repository_ref: str
    repository_id: int
    default_branch: str


@dataclass(frozen=True, slots=True)
class VercelProjectReadinessResult:
    target: VercelApiTarget
    created: bool


class VercelProjectReadinessRestClient:
    """Minimal Vercel Project discovery/creation boundary for Preview readiness.

    This client can list, read and create Project metadata only. It has no
    deployment, promotion, domain, environment-variable or deletion operation.
    """

    def __init__(
        self,
        credential_provider: EnvironmentVercelCredentialProvider,
        *,
        credential_ref: str,
        team_id: str,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not isinstance(credential_ref, str) or not credential_ref:
            raise ValueError("readiness credential_ref is required")
        if not isinstance(team_id, str) or not team_id:
            raise ValueError("readiness team_id is required")
        if not 0 < float(timeout_seconds) <= 60:
            raise ValueError("Vercel readiness timeout must be between 0 and 60 seconds")
        self._credentials = credential_provider
        self._credential_ref = credential_ref
        self._team_id = team_id
        self._http = httpx.Client(
            base_url="https://api.vercel.com",
            transport=transport,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )

    def _headers(self) -> dict[str, str]:
        try:
            credential = self._credentials.credential_for_project(self._credential_ref)
        except ProviderClientError:
            raise
        except Exception:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from None
        credential = require_scoped_credential(
            credential,
            provider="vercel",
            resource_ref=self._credential_ref,
        )
        return {
            "Authorization": credential.authorization_value(),
            "Content-Type": "application/json",
            "User-Agent": "Parallax-App-Builder",
        }

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        body: dict[str, object] | None = None,
    ) -> httpx.Response:
        query = dict(params or {})
        query["teamId"] = self._team_id
        try:
            return self._http.request(
                method,
                path,
                headers=self._headers(),
                params=query,
                json=body,
            )
        except ProviderClientError:
            raise
        except httpx.TimeoutException:
            raise ProviderClientError("PROVIDER_TIMEOUT") from None
        except httpx.RequestError:
            raise ProviderClientError("PROVIDER_UNAVAILABLE") from None

    @staticmethod
    def _payload(response: httpx.Response) -> dict[str, object]:
        try:
            value = response.json()
        except Exception:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from None
        if not isinstance(value, dict):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        return value

    @staticmethod
    def _raise_status(response: httpx.Response, *, conflict_ok: bool = False) -> None:
        if 200 <= response.status_code < 300:
            return
        if conflict_ok and response.status_code == 409:
            return
        if response.status_code in {401, 403}:
            raise ProviderClientError("PROVIDER_AUTH_DENIED")
        if response.status_code == 404:
            raise ProviderClientError("TARGET_NOT_FOUND")
        if response.status_code == 409:
            raise ProviderClientError("PROVIDER_CONFLICT")
        if response.status_code == 429:
            raise ProviderClientError("PROVIDER_RATE_LIMITED")
        if response.status_code >= 500:
            raise ProviderClientError("PROVIDER_UNAVAILABLE")
        raise ProviderClientError("PROVIDER_REJECTED")

    @staticmethod
    def _repo_id(value: object) -> int | None:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
        return None

    def _verify_project(
        self,
        payload: dict[str, object],
        *,
        repository_ref: str,
        github_repo_id: int,
        production_branch: str,
        created: bool,
    ) -> VercelProjectReadinessResult:
        project_id = payload.get("id")
        project_name = payload.get("name")
        if not isinstance(project_id, str) or not project_id:
            raise ProviderClientError("TARGET_IDENTITY_UNVERIFIED")
        if not isinstance(project_name, str) or not _PROJECT_NAME.fullmatch(project_name):
            raise ProviderClientError("TARGET_IDENTITY_UNVERIFIED")
        account_id = payload.get("accountId")
        if not isinstance(account_id, str) or account_id != self._team_id:
            raise ProviderClientError("TARGET_SCOPE_MISMATCH", result_identity=project_id)
        link = payload.get("link")
        if not isinstance(link, dict) or link.get("type") != "github":
            raise ProviderClientError("TARGET_REPOSITORY_UNVERIFIED", result_identity=project_id)
        if self._repo_id(link.get("repoId")) != github_repo_id:
            raise ProviderClientError("TARGET_REPOSITORY_MISMATCH", result_identity=project_id)
        target = VercelApiTarget(
            vercel_project_ref=f"vercel:{project_id}",
            project_id=project_id,
            project_name=project_name,
            team_id=self._team_id,
            repository_ref=repository_ref,
            github_repo_id=github_repo_id,
            production_branch=production_branch,
        )
        return VercelProjectReadinessResult(target=target, created=created)

    def _read(
        self,
        project_id: str,
        *,
        repository_ref: str,
        github_repo_id: int,
        production_branch: str,
        created: bool,
    ) -> VercelProjectReadinessResult:
        response = self._send("GET", f"/v9/projects/{quote(project_id, safe='')}")
        self._raise_status(response)
        return self._verify_project(
            self._payload(response),
            repository_ref=repository_ref,
            github_repo_id=github_repo_id,
            production_branch=production_branch,
            created=created,
        )

    def _matches(self, *, github_repo_id: int) -> list[dict[str, object]]:
        response = self._send("GET", "/v9/projects", params={"limit": _MAX_PROJECTS})
        self._raise_status(response)
        payload = self._payload(response)
        projects = payload.get("projects")
        if not isinstance(projects, list):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        pagination = payload.get("pagination")
        if isinstance(pagination, dict) and pagination.get("next") not in {None, 0, ""}:
            raise ProviderClientError("TARGET_DISCOVERY_UNBOUNDED")
        matches: list[dict[str, object]] = []
        for item in projects:
            if not isinstance(item, dict):
                continue
            link = item.get("link")
            if isinstance(link, dict) and link.get("type") == "github" and self._repo_id(link.get("repoId")) == github_repo_id:
                matches.append(item)
        return matches

    def _assert_no_production_deployment(self, *, project_id: str) -> None:
        response = self._send(
            "GET",
            "/v6/deployments",
            params={"projectId": project_id, "target": "production", "limit": 1},
        )
        self._raise_status(response)
        payload = self._payload(response)
        deployments = payload.get("deployments")
        if not isinstance(deployments, list):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        if deployments:
            raise ProviderClientError("PRODUCTION_DEPLOYMENT_SIDE_EFFECT", result_identity=project_id)

    def ensure(
        self,
        *,
        repository_ref: str,
        github_repo_id: int,
        production_branch: str,
        project_name: str,
    ) -> VercelProjectReadinessResult:
        matches = self._matches(github_repo_id=github_repo_id)
        if len(matches) > 1:
            raise ProviderClientError("TARGET_AMBIGUOUS")
        if len(matches) == 1:
            project_id = matches[0].get("id")
            if not isinstance(project_id, str) or not project_id:
                raise ProviderClientError("TARGET_IDENTITY_UNVERIFIED")
            return self._read(
                project_id,
                repository_ref=repository_ref,
                github_repo_id=github_repo_id,
                production_branch=production_branch,
                created=False,
            )

        repository = repository_ref.removeprefix("github:")
        response = self._send(
            "POST",
            "/v11/projects",
            body={
                "name": project_name,
                "gitRepository": {"type": "github", "repo": repository},
            },
        )
        if response.status_code == 409:
            matches = self._matches(github_repo_id=github_repo_id)
            if len(matches) != 1:
                raise ProviderClientError("PROVIDER_CONFLICT")
            project_id = matches[0].get("id")
            if not isinstance(project_id, str) or not project_id:
                raise ProviderClientError("TARGET_IDENTITY_UNVERIFIED")
            result = self._read(
                project_id,
                repository_ref=repository_ref,
                github_repo_id=github_repo_id,
                production_branch=production_branch,
                created=False,
            )
            # A conflict can mean another concurrent readiness request created
            # the Project. Treat that reconciled Project as newly readied for
            # this operation and prove no production deployment appeared before
            # admitting it as the Preview target.
            self._assert_no_production_deployment(project_id=project_id)
            return result
        self._raise_status(response)
        created_payload = self._payload(response)
        project_id = created_payload.get("id")
        if not isinstance(project_id, str) or not project_id:
            raise ProviderClientError("TARGET_IDENTITY_UNVERIFIED")
        result = self._read(
            project_id,
            repository_ref=repository_ref,
            github_repo_id=github_repo_id,
            production_branch=production_branch,
            created=True,
        )
        self._assert_no_production_deployment(project_id=project_id)
        return result


class VercelProjectReadinessActions:
    """One project-scoped provider mutation: ensure the exact Preview container."""

    def __init__(self, registry: ToolCapabilityRegistry, client: VercelProjectReadinessRestClient) -> None:
        self.executor = AuthorizedProviderExecutor(registry)
        self.client = client

    def ensure(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        github_repo_id: int,
        production_branch: str,
        project_name: str,
    ):
        request, decision = self.executor.authorize(
            binding=binding,
            invocation=invocation,
            tool="vercel",
            action=ACTION_PROJECT_ENSURE,
        )
        try:
            value = safe_provider_call(
                lambda: self.client.ensure(
                    repository_ref=binding.repository_ref,
                    github_repo_id=github_repo_id,
                    production_branch=production_branch,
                    project_name=project_name,
                )
            )
            if value.target.repository_ref != binding.repository_ref:
                raise ProviderClientError("REPOSITORY_MISMATCH", result_identity=value.target.project_id)
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_PROJECT_ENSURE,
                error=exc,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_PROJECT_ENSURE,
            value=value,
            result_code="PROJECT_CREATED" if value.created else "PROJECT_REUSED",
            result_identity=value.target.project_id,
        )


def _configuration_raw(preview_targets_json: str | None) -> str:
    encoded = preview_targets_json if preview_targets_json is not None else os.getenv(_ENV_PREVIEW_TARGETS)
    if not isinstance(encoded, str) or not encoded.strip():
        raise ProductionDeliveryConfigurationError("Vercel Preview target registry configuration is unavailable")
    return encoded


def _provisioning_profile(encoded: str) -> DeliveryProvisioningProfile:
    # First run the accepted registry parser so profile derivation cannot admit
    # registrations the normal delivery path would reject.
    RepositoryPreviewTargetResolver.from_environment(encoded)
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise ProductionDeliveryConfigurationError("Vercel Preview target registry configuration is invalid") from exc
    profiles: set[tuple[str, str, str]] = set()
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                raise ProductionDeliveryConfigurationError("Vercel Preview target registry contains an invalid target")
            team_id = item.get("team_id")
            connector = item.get("github_connector")
            token_env = item.get("vercel_token_env")
            if not all(isinstance(value, str) and value for value in (team_id, connector, token_env)):
                raise ProductionDeliveryConfigurationError("dynamic delivery readiness requires one explicit server-owned provisioning profile")
            profiles.add((team_id, connector, token_env))
    if len(profiles) != 1:
        raise ProductionDeliveryConfigurationError("dynamic delivery readiness provisioning profile is ambiguous")
    team_id, connector, token_env = next(iter(profiles))
    return DeliveryProvisioningProfile(team_id=team_id, github_connector=connector, vercel_token_env=token_env)


def _github_identity(
    credentials: VercelConnectGitHubCredentialProvider,
    repository_ref: str,
    *,
    transport: httpx.BaseTransport | None,
) -> VerifiedGitHubRepositoryIdentity:
    credential = credentials.credential_for_repository(repository_ref)
    repository = repository_ref.removeprefix("github:")
    owner, name = repository.split("/", 1)
    http = httpx.Client(
        base_url="https://api.github.com",
        transport=transport,
        timeout=httpx.Timeout(20.0),
        follow_redirects=False,
    )
    try:
        response = http.get(
            f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": credential.authorization_value(),
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "Parallax-App-Builder",
            },
        )
    except httpx.TimeoutException:
        raise ProviderClientError("PROVIDER_TIMEOUT") from None
    except httpx.RequestError:
        raise ProviderClientError("PROVIDER_UNAVAILABLE") from None
    if response.status_code in {401, 403}:
        raise ProviderClientError("PROVIDER_AUTH_DENIED")
    if response.status_code == 404:
        raise ProviderClientError("REPOSITORY_NOT_FOUND")
    if not 200 <= response.status_code < 300:
        raise ProviderClientError("PROVIDER_REJECTED")
    try:
        payload = response.json()
    except Exception:
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from None
    if not isinstance(payload, dict):
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    full_name = payload.get("full_name")
    repository_id = payload.get("id")
    default_branch = payload.get("default_branch")
    if not isinstance(full_name, str) or full_name.casefold() != repository.casefold():
        raise ProviderClientError("REPOSITORY_MISMATCH")
    if not isinstance(repository_id, int) or isinstance(repository_id, bool) or repository_id < 1:
        raise ProviderClientError("REPOSITORY_IDENTITY_UNVERIFIED")
    if (
        not isinstance(default_branch, str)
        or not _BRANCH.fullmatch(default_branch)
        or default_branch.startswith("/")
        or "//" in default_branch
        or ".." in default_branch.split("/")
    ):
        raise ProviderClientError("REPOSITORY_IDENTITY_UNVERIFIED")
    return VerifiedGitHubRepositoryIdentity(
        repository_ref=repository_ref,
        repository_id=repository_id,
        default_branch=default_branch,
    )


def _project_name(binding: ProviderProjectBinding) -> str:
    repository_name = binding.repository_ref.removeprefix("github:").split("/", 1)[1].casefold()
    base = re.sub(r"[^a-z0-9-]+", "-", repository_name).strip("-") or "parallax-project"
    suffix = binding.project_ref.replace("-", "")[:8]
    value = f"{base[:80]}-px-{suffix}"[:100].rstrip("-")
    if not _PROJECT_NAME.fullmatch(value):
        raise ProductionDeliveryConfigurationError("canonical Project cannot derive a bounded Vercel Project name")
    return value


def _readiness_registry(project_id: str) -> tuple[ToolCapabilityRegistry, str]:
    capability_id = f"cap:vercel-readiness:{project_id}"
    return (
        ToolCapabilityRegistry(
            (
                ToolCapability(
                    capability_id=capability_id,
                    project_ref=project_id,
                    tool="vercel",
                    actions=(ToolActionPolicy(ACTION_PROJECT_ENSURE, ToolConsequence.MUTATE),),
                ),
            )
        ),
        capability_id,
    )


def _augment_targets(encoded: str, target: VercelApiTarget, profile: DeliveryProvisioningProfile) -> str:
    payload = json.loads(encoded)
    if not isinstance(payload, list):
        raise ProductionDeliveryConfigurationError("Vercel Preview target registry configuration is invalid")
    augmented = list(payload)
    augmented.append(
        {
            "vercel_project_ref": target.vercel_project_ref,
            "project_id": target.project_id,
            "project_name": target.project_name,
            "team_id": target.team_id,
            "repository_ref": target.repository_ref,
            "github_repo_id": target.github_repo_id,
            "production_branch": target.production_branch,
            "github_connector": profile.github_connector,
            "vercel_token_env": profile.vercel_token_env,
        }
    )
    return json.dumps(augmented, separators=(",", ":"), sort_keys=True)


def production_source_delivery_ready(
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
    """Use existing delivery registration or ensure one exact Project target.

    The normal accepted source-delivery stack remains authoritative after this
    readiness seam. Dynamic state is reconstructed by exact provider discovery
    on every process and is never trusted from client input.
    """

    kwargs = {
        "preview_targets_json": preview_targets_json,
        "environment": environment,
        "oidc_token": oidc_token,
        "github_transport": github_transport,
        "github_scope_transport": github_scope_transport,
        "vercel_transport": vercel_transport,
    }
    try:
        return production_source_delivery(
            session,
            owner_subject=owner_subject,
            allocator=allocator,
            project_id=project_id,
            **kwargs,
        )
    except ProductionDeliveryConfigurationError as exc:
        if str(exc) != "canonical Project repository has no registered Vercel Preview target":
            raise

    encoded = _configuration_raw(preview_targets_json)
    profile = _provisioning_profile(encoded)
    env = os.environ if environment is None else environment
    token = env.get(profile.vercel_token_env)
    if not isinstance(token, str) or not token.strip():
        raise ProductionDeliveryConfigurationError(
            "Parallax couldn't prepare this project for building yet. Your plan and work are still saved. Try again."
        )

    projects = ProjectRepository(session)
    project = projects.get_for_owner(project_id, owner_subject.strip())
    if project is None or project.status != "active" or not project.repository_ref:
        raise ProductionDeliveryConfigurationError("canonical owner-scoped Project is unavailable")
    binding = ProviderProjectBinding(project_ref=project.id, repository_ref=project.repository_ref)

    try:
        github_credentials = VercelConnectGitHubCredentialProvider(
            profile.github_connector,
            oidc_token=oidc_token,
            request_delivery_permissions=True,
            transport=github_transport,
            github_transport=github_scope_transport,
        )
        identity = _github_identity(
            github_credentials,
            binding.repository_ref,
            transport=github_transport,
        )
        credential_ref = f"readiness:{profile.team_id}"
        vercel_credentials = EnvironmentVercelCredentialProvider(
            token,
            allowed_targets=frozenset({credential_ref}),
        )
        registry, capability_id = _readiness_registry(project.id)
        client = VercelProjectReadinessRestClient(
            vercel_credentials,
            credential_ref=credential_ref,
            team_id=profile.team_id,
            transport=vercel_transport,
        )
        action = VercelProjectReadinessActions(registry, client)
        operation_digest = sha256(f"{project.id}|{binding.repository_ref}|delivery-readiness".encode("utf-8")).hexdigest()[:48]
        ready = action.ensure(
            binding,
            ProviderInvocation(
                request_id=f"request:{operation_digest}",
                capability_id=capability_id,
                actor_ref="actor:parallax-runtime",
            ),
            github_repo_id=identity.repository_id,
            production_branch=identity.default_branch,
            project_name=_project_name(binding),
        ).value
    except (ProviderActionFailed, ProviderClientError, ValueError) as exc:
        raise ProductionDeliveryConfigurationError(
            "Parallax couldn't prepare this project for building yet. Your plan and work are still saved. Try again."
        ) from exc

    augmented = _augment_targets(encoded, ready.target, profile)
    return production_source_delivery(
        session,
        owner_subject=owner_subject,
        allocator=allocator,
        project_id=project_id,
        preview_targets_json=augmented,
        environment=environment,
        oidc_token=oidc_token,
        github_transport=github_transport,
        github_scope_transport=github_scope_transport,
        vercel_transport=vercel_transport,
    )


__all__ = [
    "ACTION_PROJECT_ENSURE",
    "DeliveryProvisioningProfile",
    "VercelProjectReadinessActions",
    "VercelProjectReadinessRestClient",
    "VercelProjectReadinessResult",
    "VerifiedGitHubRepositoryIdentity",
    "production_source_delivery_ready",
]
