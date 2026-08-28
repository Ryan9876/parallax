from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from ..projects.repository import ProjectRepository
from ..tools.contracts import ToolActionPolicy, ToolCapability, ToolConsequence
from ..tools.providers import (
    ACTION_REPOSITORY_RESOLVE,
    ACTION_SOURCE_FILE_READ,
    ACTION_SOURCE_TREE_READ,
    GITHUB_TOOL,
    GitHubProviderActions,
)
from ..tools.providers.github_client import GitHubRestProviderClient
from ..tools.registry import ToolCapabilityRegistry
from .delivery_readiness import _configuration_raw, _provisioning_profile
from .production_delivery import (
    ProductionDeliveryConfigurationError,
    VercelConnectGitHubCredentialProvider,
)
from .production_source_projection import ProjectedRepositoryLineageBootstrap
from .source_delivery_composition import (
    OwnerScopedProjectBindingResolver,
    ScopedProviderInvocationFactory,
)


class VercelConnectGitHubBootstrapCredentialProvider(VercelConnectGitHubCredentialProvider):
    """Use the existing request-scoped Connect exchange with read-only GitHub scope."""

    @staticmethod
    def delivery_authorization_details(repository: str) -> list[dict[str, object]]:
        return [
            {
                "type": "github_app_installation",
                "repositories": [repository],
                "permissions": ["contents:read", "metadata:read"],
            }
        ]


def _bootstrap_registry(project_id: str) -> tuple[ToolCapabilityRegistry, str]:
    capability_id = f"cap:github-bootstrap:{project_id}"
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                capability_id=capability_id,
                project_ref=project_id,
                tool=GITHUB_TOOL,
                actions=(
                    ToolActionPolicy(ACTION_REPOSITORY_RESOLVE, ToolConsequence.READ),
                    ToolActionPolicy(ACTION_SOURCE_TREE_READ, ToolConsequence.READ),
                    ToolActionPolicy(ACTION_SOURCE_FILE_READ, ToolConsequence.READ),
                ),
            ),
        )
    )
    return registry, capability_id


def production_source_bootstrap(
    session: Session,
    *,
    owner_subject: str,
    allocator: object,
    project_id: str,
    preview_targets_json: str | None = None,
    oidc_token: str | None = None,
    github_transport: httpx.BaseTransport | None = None,
    github_scope_transport: httpx.BaseTransport | None = None,
) -> ProjectedRepositoryLineageBootstrap:
    """Compose canonical repository lineage without requiring a Vercel target.

    PLAN needs exact repository source context. It does not need hosting metadata.
    The server derives one accepted Connect profile from the existing protected
    delivery configuration, requests an exact repository-scoped read credential,
    and exposes only GitHub read capabilities to the bootstrap path.
    """

    if not isinstance(owner_subject, str) or not owner_subject.strip():
        raise ProductionDeliveryConfigurationError(
            "owner-scoped production source bootstrap requires an authenticated subject"
        )
    encoded = _configuration_raw(preview_targets_json)
    profile = _provisioning_profile(encoded)

    projects = ProjectRepository(session)
    project = projects.get_for_owner(project_id, owner_subject.strip())
    if project is None or project.status != "active":
        raise ProductionDeliveryConfigurationError("canonical owner-scoped Project is unavailable")
    if not project.repository_ref or not project.repository_ref.startswith("github:"):
        raise ProductionDeliveryConfigurationError(
            "canonical Project requires a GitHub repository binding for source bootstrap"
        )

    registry, github_capability_id = _bootstrap_registry(project.id)
    # ScopedProviderInvocationFactory requires both fixed IDs by contract, but
    # this registry contains no Vercel capability and bootstrap never requests
    # a Vercel action. The inert ID cannot authorize anything.
    invocations = ScopedProviderInvocationFactory(
        github_capability_id=github_capability_id,
        vercel_capability_id=f"cap:vercel-inert:{project.id}",
        actor_ref="actor:parallax-runtime",
    )
    credentials = VercelConnectGitHubBootstrapCredentialProvider(
        profile.github_connector,
        oidc_token=oidc_token,
        request_delivery_permissions=True,
        transport=github_transport,
        github_transport=github_scope_transport,
    )
    github = GitHubProviderActions(registry, GitHubRestProviderClient(credentials))
    bindings = OwnerScopedProjectBindingResolver(projects, owner_subject=owner_subject.strip())
    return ProjectedRepositoryLineageBootstrap(
        allocator=allocator,
        projects=bindings,
        github=github,
        invocations=invocations,
    )


__all__ = [
    "VercelConnectGitHubBootstrapCredentialProvider",
    "production_source_bootstrap",
]
