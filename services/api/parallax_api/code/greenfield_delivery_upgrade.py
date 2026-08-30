from __future__ import annotations

from ..tools.contracts import ToolActionPolicy, ToolCapability, ToolConsequence
from ..tools.providers import GITHUB_TOOL
from ..tools.providers.github_client import GitHubRestProviderClient
from ..tools.registry import ToolCapabilityRegistry
from .greenfield_composition import GreenfieldVerifiedLineageDelivery
from .greenfield_github import (
    ACTION_REPOSITORY_INITIALIZE_EMPTY,
    GreenfieldGitHubActions,
    GreenfieldGitHubClient,
)
from .source_delivery_composition import SourceDeliveryComposition, VerifiedLineageDelivery


def upgrade_greenfield_delivery(
    composition: SourceDeliveryComposition,
    *,
    project_id: str,
) -> SourceDeliveryComposition:
    """Add a separate REVIEW-only empty-baseline mutation capability.

    The already-qualified delivery stack owns repository credentials and exact
    target verification. Greenfield initialization reuses that credentialed REST
    client but receives a distinct server-owned capability containing only the
    fixed `repository.initialize-empty` mutation. Existing branch/commit/PR
    authority is not widened and no new credential is introduced.
    """

    delivery = composition.delivery
    if isinstance(delivery, GreenfieldVerifiedLineageDelivery):
        return composition
    if not isinstance(delivery, VerifiedLineageDelivery):
        return composition
    if not isinstance(project_id, str) or not project_id or delivery.projects.resolve(project_id).project_ref != project_id:
        raise ValueError("greenfield delivery requires the canonical Project identity")

    github_client = delivery.github.client
    if not isinstance(github_client, GitHubRestProviderClient):
        raise TypeError("greenfield delivery requires the protected GitHub REST client")

    capability_id = f"cap:github-greenfield-delivery:{project_id}"
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                capability_id=capability_id,
                project_ref=project_id,
                tool=GITHUB_TOOL,
                actions=(
                    ToolActionPolicy(
                        ACTION_REPOSITORY_INITIALIZE_EMPTY,
                        ToolConsequence.MUTATE,
                    ),
                ),
            ),
        )
    )
    greenfield = GreenfieldGitHubActions(
        registry,
        GreenfieldGitHubClient(github_client),
    )
    upgraded = GreenfieldVerifiedLineageDelivery(
        allocator=delivery.allocator,
        projects=delivery.projects,
        preview_targets=delivery.preview_targets,
        github=delivery.github,
        vercel=delivery.vercel,
        invocations=delivery.invocations,
        records=delivery.records,
        greenfield=greenfield,
        github_capability_id=capability_id,
    )
    return SourceDeliveryComposition(
        bootstrap=composition.bootstrap,
        delivery=upgraded,
    )


__all__ = ["upgrade_greenfield_delivery"]
