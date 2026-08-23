from __future__ import annotations

from sqlalchemy.orm import Session

from ..code.source_delivery_composition import SourceDeliveryComposition
from ..projects.repository import ProjectRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from ..tools.providers.common import ProviderActionState
from .runtime_evidence import (
    PersistedProviderActionFact,
    PersistedVerifiedDelivery,
    RuntimeEvidenceError,
    VerifiedSourceDeliveryReader,
)


class SourceDeliveryCompositionEvidenceReader(VerifiedSourceDeliveryReader):
    """Read #80 evidence from the accepted #79 durable delivery contract.

    This adapter is intentionally read-only. It does not rerun provider calls,
    create a parallel audit store, or gain mutation/release authority. The
    accepted #79 SourceDeliveryComposition resolves its append-only Engineering
    Attempt delivery record, and this class projects those bounded facts into
    #80's evidence-only read model.
    """

    def __init__(
        self,
        session: Session,
        *,
        owner_subject: str,
        source_delivery: SourceDeliveryComposition,
    ) -> None:
        if not isinstance(owner_subject, str) or not owner_subject.strip():
            raise ValueError("owner_subject is required")
        if not isinstance(source_delivery, SourceDeliveryComposition):
            raise TypeError("source_delivery must be SourceDeliveryComposition")
        self.runs = EngineeringRunRepository(session)
        self.projects = ProjectRepository(session)
        self.owner_subject = owner_subject.strip()
        self.source_delivery = source_delivery

    def get_verified_delivery(
        self,
        *,
        project_id: str,
        run_id: str,
        lineage_id: str,
    ) -> PersistedVerifiedDelivery | None:
        run = self.runs.get(run_id)
        if run is None:
            return None
        if run.project_id != project_id:
            raise RuntimeEvidenceError("source-delivery read Project/run identity mismatch")
        project = self.projects.get_for_owner(project_id, self.owner_subject)
        if project is None or not project.repository_ref:
            raise RuntimeEvidenceError("source-delivery read requires owner-scoped Project repository binding")

        result = self.source_delivery.resolve_delivery(run)
        if result is None:
            return None
        if result.project_id != project_id or result.run_id != run_id or result.lineage_id != lineage_id:
            raise RuntimeEvidenceError("source-delivery record does not match requested Project/run/lineage")

        actions = tuple(PersistedProviderActionFact(item.evidence, item.audit) for item in result.actions)
        if not actions:
            raise RuntimeEvidenceError("source-delivery record contains no provider/audit facts")
        if any(item.evidence.repository_identity_digest != result.repository_identity_digest for item in actions):
            raise RuntimeEvidenceError("source-delivery provider evidence repository identity mismatch")

        repository_resolves = [
            item.evidence
            for item in actions
            if item.evidence.provider == "github"
            and item.evidence.action == "repository.resolve"
            and item.evidence.state is ProviderActionState.SUCCEEDED
            and item.evidence.source_revision is not None
        ]
        if len(repository_resolves) != 1:
            raise RuntimeEvidenceError("source-delivery record lacks one authoritative repository parent revision")
        expected_parent_revision = repository_resolves[0].source_revision
        if expected_parent_revision is None:  # defensive narrowing
            raise RuntimeEvidenceError("source-delivery repository parent revision is unavailable")

        return PersistedVerifiedDelivery(
            project_id=result.project_id,
            run_id=result.run_id,
            repository_ref=project.repository_ref,
            lineage_id=result.lineage_id,
            content_digest=result.content_digest,
            expected_parent_revision=expected_parent_revision,
            published_revision=result.commit_revision,
            pull_request_identity=f"pr:{result.pull_request_number}",
            preview_deployment_id=result.preview_deployment_id,
            preview_status=result.preview_status,
            actions=actions,
            publication_replayed=result.replayed,
        )


__all__ = ["SourceDeliveryCompositionEvidenceReader"]
