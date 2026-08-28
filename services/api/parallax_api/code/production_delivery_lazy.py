from __future__ import annotations

from typing import Mapping

import httpx
from sqlalchemy.orm import Session

from .delivery_readiness import production_source_delivery_ready
from .production_bootstrap import production_source_bootstrap
from .source_delivery_composition import SourceDeliveryComposition, VerifiedDeliveryResult


class DeferredVerifiedLineageDelivery:
    """Resolve Preview readiness only when verified REVIEW delivery is attempted.

    Canonical source bootstrap is intentionally independent of Vercel Project
    readiness. This adapter retains the accepted VerifiedLineageDelivery contract
    at the point it is actually needed while keeping PLAN/IMPLEMENT/BUILD/TEST/
    VERIFY free of Preview-target discovery or creation.
    """

    def __init__(
        self,
        session: Session,
        *,
        owner_subject: str,
        allocator: object,
        project_id: str,
        preview_targets_json: str | None,
        environment: Mapping[str, str] | None,
        oidc_token: str | None,
        github_transport: httpx.BaseTransport | None,
        github_scope_transport: httpx.BaseTransport | None,
        vercel_transport: httpx.BaseTransport | None,
    ) -> None:
        self._session = session
        self._owner_subject = owner_subject
        self._allocator = allocator
        self._project_id = project_id
        self._kwargs = {
            "preview_targets_json": preview_targets_json,
            "environment": environment,
            "oidc_token": oidc_token,
            "github_transport": github_transport,
            "github_scope_transport": github_scope_transport,
            "vercel_transport": vercel_transport,
        }
        self._resolved: SourceDeliveryComposition | None = None

    def _resolve_for_delivery(self) -> SourceDeliveryComposition:
        current = self._resolved
        if current is not None:
            return current
        current = production_source_delivery_ready(
            self._session,
            owner_subject=self._owner_subject,
            allocator=self._allocator,
            project_id=self._project_id,
            **self._kwargs,
        )
        self._resolved = current
        return current

    def deliver(self, run, *, operation_key: str) -> VerifiedDeliveryResult:
        return self._resolve_for_delivery().delivery.deliver(
            run,
            operation_key=operation_key,
        )

    def resolve_record(self, run) -> VerifiedDeliveryResult | None:
        # Reading a record must never create provider infrastructure. A request
        # that already resolved delivery can reuse its exact composition; a fresh
        # request simply reports no in-request record through this optional seam.
        if self._resolved is None:
            return None
        return self._resolved.delivery.resolve_record(run)


def production_source_delivery_lazy(
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
    """Compose read-only source bootstrap plus deferred verified delivery.

    This is the W8-S2 production composition boundary. It deliberately does not
    inspect, discover, or create a Vercel Project. The first Vercel readiness
    operation can occur only from ``delivery.deliver`` after protected execution
    has already reached the existing REVIEW boundary.
    """

    bootstrap = production_source_bootstrap(
        session,
        owner_subject=owner_subject,
        allocator=allocator,
        project_id=project_id,
        preview_targets_json=preview_targets_json,
        oidc_token=oidc_token,
        github_transport=github_transport,
        github_scope_transport=github_scope_transport,
    )
    deferred = DeferredVerifiedLineageDelivery(
        session,
        owner_subject=owner_subject,
        allocator=allocator,
        project_id=project_id,
        preview_targets_json=preview_targets_json,
        environment=environment,
        oidc_token=oidc_token,
        github_transport=github_transport,
        github_scope_transport=github_scope_transport,
        vercel_transport=vercel_transport,
    )
    # SourceDeliveryComposition is intentionally a narrow structural contract.
    # DeferredVerifiedLineageDelivery implements the two delivery methods used by
    # that contract while delaying provider readiness to its correct lifecycle.
    return SourceDeliveryComposition(bootstrap=bootstrap, delivery=deferred)  # type: ignore[arg-type]


__all__ = [
    "DeferredVerifiedLineageDelivery",
    "production_source_delivery_lazy",
]
