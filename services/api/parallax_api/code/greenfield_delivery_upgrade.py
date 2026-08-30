from __future__ import annotations

from .greenfield_composition import GreenfieldVerifiedLineageDelivery
from .greenfield_github import GreenfieldGitHubActions, GreenfieldGitHubClient
from .source_delivery_composition import SourceDeliveryComposition, VerifiedLineageDelivery
from ..tools.providers.github_client import GitHubRestProviderClient


def upgrade_greenfield_delivery(composition: SourceDeliveryComposition) -> SourceDeliveryComposition:
    """Add greenfield REVIEW initialization to an already-qualified Preview stack.

    Readiness continues to own credential/target verification. This adapter
    reuses that exact registry, REST client, invocation authority and record
    store; it creates no additional provider credential or capability.
    """

    delivery = composition.delivery
    if isinstance(delivery, GreenfieldVerifiedLineageDelivery):
        return composition
    if not isinstance(delivery, VerifiedLineageDelivery):
        return composition
    github_client = delivery.github.client
    if not isinstance(github_client, GitHubRestProviderClient):
        raise TypeError("greenfield delivery requires the protected GitHub REST client")
    invocations = delivery.invocations
    capability_id = getattr(invocations, "github_capability_id", None)
    if not isinstance(capability_id, str) or not capability_id:
        raise TypeError("greenfield delivery requires fixed GitHub capability identity")
    registry = delivery.github.executor.registry
    greenfield = GreenfieldGitHubActions(registry, GreenfieldGitHubClient(github_client))
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
    return SourceDeliveryComposition(bootstrap=composition.bootstrap, delivery=upgraded)


__all__ = ["upgrade_greenfield_delivery"]
