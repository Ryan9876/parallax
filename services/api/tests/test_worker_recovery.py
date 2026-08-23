from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from parallax_api.auth import AccessPrincipal, access_principal
from parallax_api.code.worker_recovery import (
    RecoveryAction,
    StallClassification,
    WorkerCheckpoint,
    WorkerCheckpointError,
    WorkerLeaseConflict,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerStaleLease,
    WorkerStallEvidence,
    classify_stall,
)
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.db import Base, get_session, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.models import EngineeringAttempt, EngineeringRun
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.routes.conversations import router as conversations_router
from parallax_api.routes.engineering_runs import router as engineering_runs_router
from parallax_api.routes.work_specifications import router as work_specifications_router


# All unit/recovery transitions use relative offsets from a deterministic epoch.
# The epoch is intentionally future-dated so the one HTTP health test, whose
# server clock is real time, observes the synthetic lease as active instead of
# making the assertion depend on when CI happens to run.
T0 = datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)
LINEAGE_A = "src:" + "a" * 64
LINEAGE_B = "src:" + "b" * 64


@dataclass(frozen=True)
class RunBinding:
    run_id: str
    project_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def db_context(tmp_path, name: str = "worker-recovery.db"):
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    # Importing EngineeringWorkerExecution registers the Wave 3 table on Base.
    assert EngineeringWorkerExecution.__tablename__ == "engineering_worker_executions"
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def insert_bound_run(Session) -> RunBinding:
    binding = RunBinding(
        run_id=str(uuid4()),
        project_id=str(uuid4()),
        work_specification_id=str(uuid4()),
        work_specification_revision=3,
        work_specification_digest="d" * 64,
    )
    with Session() as session:
        session.add(
            EngineeringRun(
                id=binding.run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.16.1",
                project_id=binding.project_id,
                work_specification_id=binding.work_specification_id,
                work_specification_revision=binding.work_specification_revision,
                work_specification_digest=binding.work_specification_digest,
                state="IMPLEMENT",
                revision=0,
                workspace_ref=None,
            )
        )
        session.commit()
    return binding


def recovery_service(Session, **bounds):
    session = Session()
    return session, WorkerRecoveryService(
        WorkerExecutionRepository(session),
        EngineeringRunRepository(session),
        **bounds,
    )


def checkpoint(
    binding: RunBinding,
    *,
    step: str = "IMPLEMENT",
    lineage: str | None = LINEAGE_A,
    lkg: str | None = None,
    evidence_refs: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    blocker_code: str | None = None,
    plan_ref: str = "spec:P2-V0.16.1",
) -> WorkerCheckpoint:
    return WorkerCheckpoint(
        project_id=binding.project_id,
        run_id=binding.run_id,
        work_specification_id=binding.work_specification_id,
        work_specification_revision=binding.work_specification_revision,
        work_specification_digest=binding.work_specification_digest,
        plan_ref=plan_ref,
        current_step=step,
        source_lineage_ref=lineage,
        last_known_good_lineage_ref=lkg,
        evidence_refs=evidence_refs,
        dependencies=dependencies,
        blocker_code=blocker_code,
    )


def test_lease_renewal_does_not_fake_progress_and_checkpoint_binds_authoritative_lineage(tmp_path):
    Session = db_context(tmp_path)
    binding = insert_bound_run(Session)
    session, service = recovery_service(Session)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0, lease_seconds=30)
        initial = service.executions.get_for_run(binding.run_id)
        assert initial is not None
        assert initial.lease_generation == 1
        assert _aware(initial.last_meaningful_progress_at) == T0

        service.renew(lease, now=T0 + timedelta(seconds=5), lease_seconds=30)
        after_renew = service.executions.get_for_run(binding.run_id)
        assert after_renew is not None
        assert _aware(after_renew.last_meaningful_progress_at) == T0
        assert after_renew.no_progress_count == 0

        cp = checkpoint(binding, lkg=LINEAGE_A, dependencies=("workstream:96",))
        result = service.checkpoint(
            lease,
            cp,
            authoritative_source_lineage_ref=LINEAGE_A,
            now=T0 + timedelta(seconds=10),
        )
        assert result.meaningful_progress is True
        assert result.execution.checkpoint_revision == 1
        assert result.execution.state == "CHECKPOINTED"
        stored = json.loads(result.execution.checkpoint_json)
        assert stored["project_id"] == binding.project_id
        assert stored["engineering_run_revision"] == 0
        assert stored["attempt_count"] == 0
        assert stored["retry_count"] == 0

        repeated = service.checkpoint(
            lease,
            cp,
            authoritative_source_lineage_ref=LINEAGE_A,
            now=T0 + timedelta(seconds=15),
        )
        assert repeated.meaningful_progress is False
        assert repeated.execution.no_progress_count == 1
        assert _aware(repeated.execution.last_meaningful_progress_at) == T0 + timedelta(seconds=10)

        with pytest.raises(WorkerCheckpointError, match="server-resolved accepted lineage"):
            service.checkpoint(
                lease,
                cp,
                authoritative_source_lineage_ref=LINEAGE_B,
                now=T0 + timedelta(seconds=16),
            )
        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            service.checkpoint(
                lease,
                replace(cp, plan_ref="spec:P2-V0.16.99"),
                authoritative_source_lineage_ref=LINEAGE_A,
                now=T0 + timedelta(seconds=16),
            )
    finally:
        session.close()


def test_checkpoint_rejects_identity_secret_reasoning_command_and_url_injection(tmp_path):
    Session = db_context(tmp_path)
    binding = insert_bound_run(Session)
    session, service = recovery_service(Session)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0)
        baseline = checkpoint(binding)
        bad = (
            replace(baseline, project_id=str(uuid4())),
            replace(baseline, work_specification_digest="e" * 64),
            replace(baseline, evidence_refs=("secret:abcdefgh",)),
            replace(baseline, evidence_refs=("scratchpad:private",)),
            replace(baseline, evidence_refs=("command:rm-rf",)),
            replace(baseline, dependencies=("https://example.invalid/work",)),
            replace(baseline, source_lineage_ref="src:not-a-digest"),
            replace(baseline, dependencies=("workstream:96", "workstream:96")),
            replace(baseline, blocker_code="not a bounded code"),
        )
        for candidate in bad:
            with pytest.raises(WorkerCheckpointError):
                service.checkpoint(
                    lease,
                    candidate,
                    authoritative_source_lineage_ref=LINEAGE_A,
                    now=T0 + timedelta(seconds=1),
                )
        current = service.executions.get_for_run(binding.run_id)
        assert current is not None
        assert current.checkpoint_revision == 0
        assert current.checkpoint_json == "{}"
    finally:
        session.close()


def test_expired_owner_requires_explicit_stall_recovery_then_reassignment(tmp_path):
    Session = db_context(tmp_path)
    binding = insert_bound_run(Session)
    session, service = recovery_service(Session)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0, lease_seconds=5)
        expired = T0 + timedelta(seconds=6)
        with pytest.raises(WorkerStaleLease):
            service.renew(lease, now=expired, lease_seconds=5)
        with pytest.raises(WorkerLeaseExpired):
            service.acquire(run_id=binding.run_id, now=expired, lease_seconds=5)
        with pytest.raises(WorkerLeaseConflict, match="RECOVERING"):
            service.reassign(run_id=binding.run_id, now=expired, lease_seconds=5)

        decision = service.classify_and_stall(
            run_id=binding.run_id,
            evidence=WorkerStallEvidence(process_lost=True),
            blocker_code="PROCESS_LOST",
            now=expired,
        )
        assert decision.classification is StallClassification.PROCESS_LOSS
        assert decision.action is RecoveryAction.REASSIGN
        service.begin_recovery(run_id=binding.run_id, now=expired + timedelta(seconds=1))
        replacement = service.reassign(
            run_id=binding.run_id,
            now=expired + timedelta(seconds=2),
            lease_seconds=10,
        )
        assert replacement.generation == lease.generation + 1
        assert replacement.owner_id != lease.owner_id
        with pytest.raises(WorkerStaleLease):
            service.renew(lease, now=expired + timedelta(seconds=3))
    finally:
        session.close()


def test_process_loss_preserves_checkpoint_and_one_delivery_record_across_process_recreation(tmp_path):
    Session = db_context(tmp_path)
    binding = insert_bound_run(Session)
    delivery_id = str(uuid4())
    with Session() as session:
        session.add(
            EngineeringAttempt(
                id=delivery_id,
                run_id=binding.run_id,
                stage="SOURCE_DELIVERY",
                attempt_number=1,
                operation_key="delivery:accepted-lineage-a",
                status="RECORDED",
                evidence_json=json.dumps(
                    {
                        "record_kind": "verified_source_delivery",
                        "source_lineage_ref": LINEAGE_A,
                        "provider_action_ids": ["provider-action:immutable-1"],
                    },
                    sort_keys=True,
                ),
            )
        )
        session.commit()

    session, service = recovery_service(Session)
    old_lease = service.acquire(run_id=binding.run_id, now=T0)
    cp = checkpoint(
        binding,
        lineage=LINEAGE_A,
        lkg=LINEAGE_A,
        evidence_refs=(f"attempt:{delivery_id}",),
        dependencies=("gate:browser",),
    )
    first = service.checkpoint(
        old_lease,
        cp,
        authoritative_source_lineage_ref=LINEAGE_A,
        now=T0 + timedelta(seconds=1),
    )
    assert first.execution.checkpoint_revision == 1
    assert json.loads(first.execution.checkpoint_json)["attempt_count"] == 1

    service.classify_and_stall(
        run_id=binding.run_id,
        evidence=WorkerStallEvidence(process_lost=True),
        blocker_code="PROCESS_LOST",
        now=T0 + timedelta(seconds=2),
    )
    service.begin_recovery(run_id=binding.run_id, now=T0 + timedelta(seconds=3))
    new_lease = service.reassign(run_id=binding.run_id, now=T0 + timedelta(seconds=4))
    assert new_lease.generation == old_lease.generation + 1

    with pytest.raises(WorkerStaleLease):
        service.checkpoint(
            old_lease,
            cp,
            authoritative_source_lineage_ref=LINEAGE_A,
            now=T0 + timedelta(seconds=5),
        )
    resumed = service.checkpoint(
        new_lease,
        cp,
        authoritative_source_lineage_ref=LINEAGE_A,
        state=WorkerLifecycleState.PROGRESSING,
        now=T0 + timedelta(seconds=5),
    )
    assert resumed.execution.source_lineage_ref == LINEAGE_A
    assert resumed.execution.last_known_good_lineage_ref == LINEAGE_A
    session.close()

    recreated_session, recreated = recovery_service(Session)
    try:
        health = recreated.health(run_id=binding.run_id, now=T0 + timedelta(seconds=6))
        assert health.project_id == binding.project_id
        assert health.lease_status == "ACTIVE"
        assert health.lease_generation == new_lease.generation
        assert health.source_lineage_ref == LINEAGE_A
        assert health.last_known_good_lineage_ref == LINEAGE_A
        assert health.dependencies == ("gate:browser",)

        rows = recreated_session.scalars(
            select(EngineeringAttempt).where(
                EngineeringAttempt.run_id == binding.run_id,
                EngineeringAttempt.stage == "SOURCE_DELIVERY",
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].id == delivery_id
        assert rows[0].operation_key == "delivery:accepted-lineage-a"
    finally:
        recreated_session.close()


def test_no_progress_retry_and_oscillation_limits_terminate_boundedly(tmp_path):
    Session = db_context(tmp_path)

    binding = insert_bound_run(Session)
    session, service = recovery_service(Session, max_no_progress=1, max_retries=99, max_oscillations=99)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0)
        cp = checkpoint(binding)
        service.checkpoint(lease, cp, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=1))
        service.checkpoint(lease, cp, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=2))
        stopped = service.checkpoint(lease, cp, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=3))
        assert stopped.bounded_stop is True
        assert stopped.execution.state == "FAILED"
        assert stopped.execution.blocker_code == "WORKER_NO_PROGRESS_LIMIT"
        assert stopped.execution.lease_owner_id is None
        with pytest.raises(WorkerLeaseConflict):
            service.acquire(run_id=binding.run_id, now=T0 + timedelta(seconds=4))
    finally:
        session.close()

    retry_binding = insert_bound_run(Session)
    retry_session, retry_service = recovery_service(Session, max_retries=1, max_no_progress=99, max_oscillations=99)
    try:
        lease = retry_service.acquire(run_id=retry_binding.run_id, now=T0)
        retry_service.checkpoint(lease, checkpoint(retry_binding, evidence_refs=("validation:base",)), authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=1))
        retry_service.checkpoint(lease, checkpoint(retry_binding, evidence_refs=("validation:r1",)), authoritative_source_lineage_ref=LINEAGE_A, retry=True, now=T0 + timedelta(seconds=2))
        stopped = retry_service.checkpoint(lease, checkpoint(retry_binding, evidence_refs=("validation:r2",)), authoritative_source_lineage_ref=LINEAGE_A, retry=True, now=T0 + timedelta(seconds=3))
        assert stopped.bounded_stop is True
        assert stopped.execution.blocker_code == "WORKER_RETRY_LIMIT"
    finally:
        retry_session.close()

    oscillation_binding = insert_bound_run(Session)
    oscillation_session, oscillation_service = recovery_service(Session, max_retries=99, max_no_progress=99, max_oscillations=1)
    try:
        lease = oscillation_service.acquire(run_id=oscillation_binding.run_id, now=T0)
        a = checkpoint(oscillation_binding, evidence_refs=("validation:defect-a",))
        b = checkpoint(oscillation_binding, evidence_refs=("validation:defect-b",))
        oscillation_service.checkpoint(lease, a, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=1))
        oscillation_service.checkpoint(lease, b, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=2))
        oscillation_service.checkpoint(lease, a, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=3))
        stopped = oscillation_service.checkpoint(lease, b, authoritative_source_lineage_ref=LINEAGE_A, now=T0 + timedelta(seconds=4))
        assert stopped.bounded_stop is True
        assert stopped.execution.blocker_code == "WORKER_OSCILLATION_LIMIT"
    finally:
        oscillation_session.close()


@pytest.mark.parametrize(
    ("evidence", "classification", "action", "human"),
    [
        (WorkerStallEvidence(process_lost=True), StallClassification.PROCESS_LOSS, RecoveryAction.REASSIGN, False),
        (WorkerStallEvidence(test_or_ci_hung=True), StallClassification.TEST_CI_HANG, RecoveryAction.RETRY, False),
        (WorkerStallEvidence(provider_unavailable=True), StallClassification.PROVIDER_OUTAGE, RecoveryAction.BACKOFF_RETRY, False),
        (WorkerStallEvidence(dependency_wait=True), StallClassification.DEPENDENCY_WAIT, RecoveryAction.WAIT_DEPENDENCY, False),
        (WorkerStallEvidence(rate_limited=True), StallClassification.RATE_LIMIT, RecoveryAction.BACKOFF_RETRY, False),
        (WorkerStallEvidence(credential_failure=True, credential_refreshable=True), StallClassification.CREDENTIAL_AUTHORIZATION, RecoveryAction.REFRESH_CREDENTIAL, False),
        (WorkerStallEvidence(credential_failure=True), StallClassification.CREDENTIAL_AUTHORIZATION, RecoveryAction.HUMAN_REQUIRED, True),
        (WorkerStallEvidence(contention_or_deadlock=True), StallClassification.CONTENTION_DEADLOCK, RecoveryAction.BACKOFF_RETRY, False),
        (WorkerStallEvidence(repeated_implementation_failure=True), StallClassification.REPEATED_IMPLEMENTATION_FAILURE, RecoveryAction.RETRY, False),
        (WorkerStallEvidence(human_approval_required=True), StallClassification.HUMAN_AUTHORITY_SPECIFICATION, RecoveryAction.HUMAN_REQUIRED, True),
        (WorkerStallEvidence(material_specification_ambiguity=True), StallClassification.HUMAN_AUTHORITY_SPECIFICATION, RecoveryAction.HUMAN_REQUIRED, True),
    ],
)
def test_stall_classification_is_deterministic(evidence, classification, action, human):
    decision = classify_stall(evidence)
    assert decision.classification is classification
    assert decision.action is action
    assert decision.human_required is human


def test_ready_for_integration_releases_mutation_lease(tmp_path):
    Session = db_context(tmp_path)
    binding = insert_bound_run(Session)
    session, service = recovery_service(Session)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0)
        ready = service.checkpoint(
            lease,
            checkpoint(binding, step="REVIEW"),
            authoritative_source_lineage_ref=LINEAGE_A,
            state=WorkerLifecycleState.READY_FOR_INTEGRATION,
            now=T0 + timedelta(seconds=1),
        )
        assert ready.execution.state == "READY_FOR_INTEGRATION"
        assert ready.execution.lease_owner_id is None
        assert ready.execution.lease_expires_at is None
        with pytest.raises(WorkerLeaseConflict):
            service.acquire(run_id=binding.run_id, now=T0 + timedelta(seconds=2))
        with pytest.raises(WorkerLeaseConflict):
            service.classify_and_stall(
                run_id=binding.run_id,
                evidence=WorkerStallEvidence(process_lost=True),
                now=T0 + timedelta(seconds=2),
            )
    finally:
        session.close()


def test_worker_recovery_migration_has_fail_closed_hosted_security_posture():
    path = Path(__file__).resolve().parents[1] / "migrations" / "20260823_0009_worker_recovery.sql"
    migration = path.read_text(encoding="utf-8").lower()
    for required in (
        "create table if not exists engineering_worker_executions",
        "references engineering_runs(id) on delete cascade",
        "constraint uq_engineering_worker_execution_run unique (run_id)",
        "constraint ck_worker_lease_pair check",
        "constraint ck_worker_checkpoint_size check",
        "constraint ck_worker_source_lineage_format check",
        "create index if not exists ix_engineering_worker_executions_state",
        "create index if not exists ix_engineering_worker_executions_lease_expiry",
        "alter table engineering_worker_executions enable row level security",
        "revoke all on table engineering_worker_executions from anon, authenticated",
    ):
        assert required in migration


def api_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'worker-health-api.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    owner = {"subject": "owner-a"}
    app = FastAPI()
    app.include_router(conversations_router)
    app.include_router(work_specifications_router)
    app.include_router(engineering_runs_router)

    def session_override():
        with Session() as session:
            yield session

    def principal_override():
        return AccessPrincipal(subject=owner["subject"], role="owner", auth_method="test")

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[access_principal] = principal_override
    return TestClient(app), Session, owner


def create_project(Session, owner_subject: str):
    with Session() as session:
        return ProjectRepository(session).create(
            owner_subject=owner_subject,
            slug=f"worker-health-{uuid4().hex[:8]}",
            name="Worker Health",
            description=None,
            repository_ref=None,
        )


def approve_spec(Session, conversation_id: str):
    with Session() as session:
        repository = WorkSpecificationRepository(session)
        draft = repository.create_draft(
            conversation_id=conversation_id,
            draft=WorkSpecificationDraft(
                title="Worker recovery health",
                objective="Prove owner-scoped durable worker health.",
                constraints=["Do not expose lease owner material."],
                acceptance_criteria=[
                    "Health reconstructs from persistence.",
                    "Cross-owner health access fails closed.",
                ],
                risks=["Worker state must not leak across Projects."],
                open_questions=[],
                confidence=0.99,
                program_version="worker-health-api-test",
            ),
            model_id="test-model",
        )
        return repository.approve(draft)


def test_worker_health_api_is_read_only_bounded_and_owner_scoped(tmp_path):
    client, Session, owner = api_context(tmp_path)
    project = create_project(Session, "owner-a")
    conversation = client.post(
        "/v1/conversations",
        json={"mode": "code", "project_id": project.id},
    ).json()
    specification = approve_spec(Session, conversation["id"])
    activated = client.post(
        "/v1/engineering-runs/activate",
        json={"conversation_id": conversation["id"], "work_specification_id": specification.id},
    )
    assert activated.status_code == 200
    run_id = activated.json()["id"]
    assert client.get(f"/v1/engineering-runs/{run_id}/worker-health").status_code == 404

    with Session() as session:
        runs = EngineeringRunRepository(session)
        run = runs.get(run_id)
        assert run is not None and run.project_id is not None
        service = WorkerRecoveryService(WorkerExecutionRepository(session), runs)
        lease = service.acquire(run_id=run_id, now=T0)
        service.checkpoint(
            lease,
            WorkerCheckpoint(
                project_id=run.project_id,
                run_id=run.id,
                work_specification_id=run.work_specification_id or "",
                work_specification_revision=run.work_specification_revision or 0,
                work_specification_digest=run.work_specification_digest or "",
                plan_ref="spec:P2-V0.16.1",
                current_step="PLAN",
                source_lineage_ref=None,
                evidence_refs=("validation:plan",),
                dependencies=("workstream:96",),
            ),
            authoritative_source_lineage_ref=None,
            now=T0 + timedelta(seconds=1),
        )

    health = client.get(f"/v1/engineering-runs/{run_id}/worker-health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["project_id"] == project.id
    assert payload["run_id"] == run_id
    assert payload["state"] == "CHECKPOINTED"
    assert payload["lease_status"] == "ACTIVE"
    assert payload["lease_generation"] == 1
    assert payload["current_step"] == "PLAN"
    assert payload["dependencies"] == ["workstream:96"]
    assert "lease_owner_id" not in payload
    assert "checkpoint_json" not in payload

    owner["subject"] = "owner-b"
    assert client.get(f"/v1/engineering-runs/{run_id}/worker-health").status_code == 404
