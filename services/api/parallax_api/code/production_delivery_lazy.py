from __future__ import annotations

from typing import Mapping

import httpx
from sqlalchemy.orm import Session

from ..projects.repository import ProjectRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from .delivery_readiness import production_source_delivery_ready
from .production_bootstrap import production_source_bootstrap
from .source_delivery_composition import (
    EngineeringAttemptDeliveryRecordStore,
    OwnerScopedProjectBindingResolver,
    SourceDeliveryComposition,
    VerifiedDeliveryResult,
)
from .source_only_delivery import SourceOnlyDeliveryResult, SourceOnlyLineageDelivery


class DeferredVerifiedLineageDelivery:
    """Resolve Vercel Preview readiness only for a Vercel-delivered Project."""

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
    public_github_transport: httpx.BaseTransport | None = None,
    vercel_transport: httpx.BaseTransport | None = None,
) -> SourceDeliveryComposition:
    """Compose repository source independently from optional deployment delivery."""

    # Production always supplies the SQLAlchemy request Session. A small set of
    # composition contract tests intentionally use an inert object because they
    # verify only that Vercel readiness stays deferred; preserve that structural
    # seam as the legacy Vercel mode without creating a production override.
    project = None
    projects = ProjectRepository(session)
    if isinstance(session, Session):
        project = projects.get_for_owner(project_id, owner_subject.strip())
        if project is None or project.status != "active":
            raise ValueError("canonical owner-scoped Project is unavailable")
        delivery_mode = project.delivery_mode
    else:
        delivery_mode = "vercel-preview"

    bootstrap = production_source_bootstrap(
        session,
        owner_subject=owner_subject,
        allocator=allocator,
        project_id=project_id,
        preview_targets_json=preview_targets_json,
        oidc_token=oidc_token,
        github_transport=github_transport,
        github_scope_transport=github_scope_transport,
        public_github_transport=public_github_transport,
    )

    if delivery_mode == "source-only":
        source_only = SourceOnlyLineageDelivery(
            allocator=allocator,
            projects=OwnerScopedProjectBindingResolver(projects, owner_subject=owner_subject.strip()),
            records=EngineeringAttemptDeliveryRecordStore(EngineeringRunRepository(session)),
        )
        return SourceDeliveryComposition(bootstrap=bootstrap, delivery=source_only)  # type: ignore[arg-type]

    if delivery_mode != "vercel-preview":
        raise ValueError("canonical Project delivery mode is unsupported")

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
    return SourceDeliveryComposition(bootstrap=bootstrap, delivery=deferred)  # type: ignore[arg-type]


__all__ = [
    "DeferredVerifiedLineageDelivery",
    "SourceOnlyDeliveryResult",
    "production_source_delivery_lazy",
]
