from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import pytest

from parallax_api.code.source_delivery_composition import (
    ProviderActionAuditPair,
    SourceDeliveryComposition,
    VerifiedDeliveryResult,
)
from parallax_api.db import Base, make_engine
from parallax_api.evaluation.runtime_evidence import RuntimeEvidenceError
from parallax_api.evaluation.source_delivery_bridge import SourceDeliveryCompositionEvidenceReader
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.tools.contracts import ToolAuditRecord, ToolConsequence, ToolOutcome
from parallax_api.tools.providers.common import (
    ProviderActionEvidence,
    ProviderActionState,
    ProviderProjectBinding,
)


OWNER = "owner:source-delivery-bridge"
REPOSITORY_REF = "github:acme/bridge-app"
PARENT_REVISION = "1" * 40
PUBLISHED_REVISION = "2" * 40
LINEAGE_ID = "src:" + "3" * 64
CONTENT_DIGEST = "4" * 64


def _pair(
    *,
    project_id: str,
    repository_digest: str,
    provider: str,
    action: str,
    result_code: str,
    result_identity: str,
    source_revision: str | None = None,
) -> ProviderActionAuditPair:
    request_id = "request:" + sha256(f"{provider}:{action}".encode()).hexdigest()[:32]
    evidence = ProviderActionEvidence(
        provider=provider,
        action=action,
        state=ProviderActionState.SUCCEEDED,
        project_ref=project_id,
        repository_identity_digest=repository_digest,
        source_revision=source_revision,
        lineage_id=LINEAGE_ID if action in {"commit.write", "pull_request.create", "preview.read"} else None,
        lineage_digest=CONTENT_DIGEST if action in {"commit.write", "pull_request.create", "preview.read"} else None,
        result_identity=result_identity,
        result_status=result_code,
    )
    audit = ToolAuditRecord(
        request_id=request_id,
        capability_id=f"cap:{provider}:bridge",
        project_ref=project_id,
        tool=provider,
        action=action,
        actor_ref="actor:bridge-test",
        consequence=ToolConsequence.MUTATE if action != "repository.resolve" else ToolConsequence.READ,
        authority_allowed=True,
        outcome=ToolOutcome.SUCCEEDED,
        deny_reason=None,
        approval_id=None,
        request_digest=sha256(f"request:{provider}:{action}".encode()).hexdigest(),
        result_digest=sha256(f"result:{provider}:{action}".encode()).hexdigest(),
        result_code=result_code,
        result_identity=result_identity,
    )
    return ProviderActionAuditPair(evidence=evidence, audit=audit)


class _DeliveryResolver:
    def __init__(self, result: VerifiedDeliveryResult):
        self.result = result
        self.calls = 0

    def resolve_record(self, run):
        self.calls += 1
        return self.result


def _environment(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'bridge.db'}")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session

    session = Session(engine)
    projects = ProjectRepository(session)
    project = projects.create(
        owner_subject=OWNER,
        slug="bridge-app",
        name="Bridge App",
        description="Source delivery evidence bridge test",
        repository_ref=REPOSITORY_REF,
    )
    conversations = ConversationRepository(session)
    conversation = conversations.create("code", spec_id="P2-V0.15.10", project_id=project.id)
    work_specs = WorkSpecificationRepository(session)
    specification = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=WorkSpecificationDraft(
            title="Bridge source delivery evidence",
            objective="Prove #80 consumes accepted #79 durable provider evidence.",
            constraints=["Do not rerun provider mutations."],
            acceptance_criteria=["Accepted delivery evidence is projected read-only."],
            risks=[],
            open_questions=[],
            confidence=0.99,
            program_version="bridge-test-v1",
        ),
        model_id="bridge-test-model",
    )
    specification = work_specs.approve(specification)
    run = EngineeringRunRepository(session).create(
        conversation_id=conversation.id,
        spec_id=conversation.spec_id,
        project_id=project.id,
        work_specification_id=specification.id,
        work_specification_revision=specification.revision,
        work_specification_digest="5" * 64,
    )
    repository_digest = ProviderProjectBinding(project.id, REPOSITORY_REF).repository_identity_digest
    actions = (
        _pair(
            project_id=project.id,
            repository_digest=repository_digest,
            provider="github",
            action="repository.resolve",
            result_code="REPOSITORY_RESOLVED",
            result_identity=PARENT_REVISION,
            source_revision=PARENT_REVISION,
        ),
        _pair(
            project_id=project.id,
            repository_digest=repository_digest,
            provider="github",
            action="commit.write",
            result_code="COMMIT_WRITTEN",
            result_identity=PUBLISHED_REVISION,
            source_revision=PUBLISHED_REVISION,
        ),
        _pair(
            project_id=project.id,
            repository_digest=repository_digest,
            provider="github",
            action="pull_request.create",
            result_code="PULL_REQUEST_CREATED",
            result_identity="pr:80",
            source_revision=PUBLISHED_REVISION,
        ),
        _pair(
            project_id=project.id,
            repository_digest=repository_digest,
            provider="vercel",
            action="preview.read",
            result_code="PREVIEW_STATUS_READY",
            result_identity="dpl_bridge_80",
            source_revision=PUBLISHED_REVISION,
        ),
    )
    result = VerifiedDeliveryResult(
        project_id=project.id,
        run_id=run.id,
        repository_identity_digest=repository_digest,
        lineage_id=LINEAGE_ID,
        content_digest=CONTENT_DIGEST,
        branch_name=f"parallax/{project.id[:8]}-{run.id[:8]}",
        commit_revision=PUBLISHED_REVISION,
        pull_request_number=80,
        pull_request_url="https://github.com/acme/bridge-app/pull/80",
        preview_deployment_id="dpl_bridge_80",
        preview_status="READY",
        preview_url="https://bridge-app-parallax.vercel.app",
        actions=actions,
        replayed=True,
    )
    resolver = _DeliveryResolver(result)
    composition = SourceDeliveryComposition(bootstrap=SimpleNamespace(), delivery=resolver)
    return session, project, run, composition, resolver


def test_bridge_projects_accepted_79_record_without_provider_mutation(tmp_path):
    session, project, run, composition, resolver = _environment(tmp_path)
    try:
        reader = SourceDeliveryCompositionEvidenceReader(
            session,
            owner_subject=OWNER,
            source_delivery=composition,
        )
        delivery = reader.get_verified_delivery(
            project_id=project.id,
            run_id=run.id,
            lineage_id=LINEAGE_ID,
        )
        assert delivery is not None
        assert delivery.repository_ref == REPOSITORY_REF
        assert delivery.expected_parent_revision == PARENT_REVISION
        assert delivery.published_revision == PUBLISHED_REVISION
        assert delivery.pull_request_identity == "pr:80"
        assert delivery.preview_deployment_id == "dpl_bridge_80"
        assert delivery.preview_status == "READY"
        assert delivery.publication_replayed is True
        assert len(delivery.actions) == 4
        assert all(item.audit.outcome is ToolOutcome.SUCCEEDED for item in delivery.actions)
        assert resolver.calls == 1
    finally:
        session.close()


def test_bridge_fails_closed_on_cross_project_read(tmp_path):
    session, project, run, composition, _resolver = _environment(tmp_path)
    try:
        reader = SourceDeliveryCompositionEvidenceReader(
            session,
            owner_subject=OWNER,
            source_delivery=composition,
        )
        with pytest.raises(RuntimeEvidenceError, match="Project/run"):
            reader.get_verified_delivery(
                project_id="00000000-0000-0000-0000-000000000001",
                run_id=run.id,
                lineage_id=LINEAGE_ID,
            )
    finally:
        session.close()
