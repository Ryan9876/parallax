from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.worker_recovery import (
    WorkerCheckpoint,
    WorkerCheckpointError,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerRecoveryError,
    WorkerStallEvidence,
)
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringAttempt, EngineeringRun
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository


T0 = datetime(2099, 8, 30, 20, 0, tzinfo=timezone.utc)
LINEAGE = "src:" + "a" * 64
OLD_PLAN_ID = "1" * 64
FRESH_PLAN_ID = "2" * 64
OTHER_PLAN_ID = "3" * 64


def _session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'p2314.db'}")
    assert EngineeringWorkerExecution.__tablename__ == "engineering_worker_executions"
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _insert_run(Session) -> EngineeringRun:
    run = EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.23.14",
        project_id=str(uuid4()),
        work_specification_id=str(uuid4()),
        work_specification_revision=1,
        work_specification_digest="d" * 64,
        state="IMPLEMENT",
        revision=5,
        workspace_ref=None,
    )
    with Session() as session:
        session.add(run)
        session.commit()
    return run


def _service(Session):
    session = Session()
    return session, WorkerRecoveryService(
        WorkerExecutionRepository(session),
        EngineeringRunRepository(session),
    )


def _checkpoint(run: EngineeringRun, plan_id: str, *, step: str) -> WorkerCheckpoint:
    return WorkerCheckpoint(
        project_id=run.project_id or "",
        run_id=run.id,
        work_specification_id=run.work_specification_id or "",
        work_specification_revision=int(run.work_specification_revision or 0),
        work_specification_digest=run.work_specification_digest or "",
        plan_ref=f"agentic-plan:{plan_id}",
        current_step=step,
        source_lineage_ref=LINEAGE,
        last_known_good_lineage_ref=LINEAGE,
        evidence_refs=(f"plan:{plan_id}",),
    )


def _append_plan_attempt(
    Session,
    run_id: str,
    *,
    attempt_number: int,
    status: str,
    evidence: dict[str, object],
    at: datetime,
) -> None:
    with Session() as session:
        session.add(
            EngineeringAttempt(
                id=str(uuid4()),
                run_id=run_id,
                stage="PLAN",
                attempt_number=attempt_number,
                operation_key=f"plan-{attempt_number}-{status.lower()}",
                status=status,
                evidence_json=json.dumps(evidence, sort_keys=True),
                started_at=at,
                completed_at=at,
            )
        )
        session.commit()


def _append_human_refresh_history(Session, run_id: str, *, fresh_plan_id: str = FRESH_PLAN_ID) -> None:
    _append_plan_attempt(
        Session,
        run_id,
        attempt_number=1,
        status="PASSED",
        evidence={
            "decision_kind": "SERVER_OWNED_AGENTIC_PLAN",
            "team_plan_id": OLD_PLAN_ID,
        },
        at=T0 - timedelta(seconds=30),
    )
    _append_plan_attempt(
        Session,
        run_id,
        attempt_number=2,
        status="RESUMED",
        evidence={
            "plan_refresh_authorized": True,
            "prior_resume_stage": "IMPLEMENT",
        },
        at=T0 + timedelta(seconds=6),
    )
    _append_plan_attempt(
        Session,
        run_id,
        attempt_number=3,
        status="PASSED",
        evidence={
            "decision_kind": "SERVER_OWNED_AGENTIC_PLAN",
            "team_plan_id": fresh_plan_id,
        },
        at=T0 + timedelta(seconds=7),
    )


def test_worker_checkpoint_error_is_both_recovery_and_value_contract_error() -> None:
    error = WorkerCheckpointError("bounded checkpoint contract failure")
    assert isinstance(error, WorkerRecoveryError)
    assert isinstance(error, ValueError)


def test_changed_plan_ref_remains_rejected_without_exact_human_refresh(tmp_path) -> None:
    Session = _session_factory(tmp_path)
    run = _insert_run(Session)
    session, service = _service(Session)
    try:
        lease = service.acquire(run_id=run.id, now=T0)
        service.checkpoint(
            lease,
            _checkpoint(run, OLD_PLAN_ID, step="AGENT_PROPOSAL"),
            authoritative_source_lineage_ref=LINEAGE,
            now=T0 + timedelta(seconds=1),
        )
        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            service.checkpoint(
                lease,
                _checkpoint(run, FRESH_PLAN_ID, step="AGENT_DISPATCH"),
                authoritative_source_lineage_ref=LINEAGE,
                now=T0 + timedelta(seconds=2),
            )
    finally:
        session.close()


def test_refresh_history_does_not_authorize_wrong_or_non_dispatch_plan_ref(tmp_path) -> None:
    Session = _session_factory(tmp_path)
    run = _insert_run(Session)
    session, service = _service(Session)
    try:
        lease = service.acquire(run_id=run.id, now=T0)
        service.checkpoint(
            lease,
            _checkpoint(run, OLD_PLAN_ID, step="AGENT_PROPOSAL"),
            authoritative_source_lineage_ref=LINEAGE,
            now=T0 + timedelta(seconds=1),
        )
        _append_human_refresh_history(Session, run.id)

        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            service.checkpoint(
                lease,
                _checkpoint(run, OTHER_PLAN_ID, step="AGENT_DISPATCH"),
                authoritative_source_lineage_ref=LINEAGE,
                now=T0 + timedelta(seconds=8),
            )
        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            service.checkpoint(
                lease,
                _checkpoint(run, FRESH_PLAN_ID, step="AGENT_RESULT"),
                authoritative_source_lineage_ref=LINEAGE,
                now=T0 + timedelta(seconds=8),
            )
    finally:
        session.close()


def test_expired_old_worker_rebinds_once_to_exact_human_refreshed_plan(tmp_path) -> None:
    Session = _session_factory(tmp_path)
    run = _insert_run(Session)
    session, service = _service(Session)
    try:
        old_lease = service.acquire(run_id=run.id, now=T0, lease_seconds=5)
        old_progress = service.checkpoint(
            old_lease,
            _checkpoint(run, OLD_PLAN_ID, step="AGENT_PROPOSAL"),
            authoritative_source_lineage_ref=LINEAGE,
            state=WorkerLifecycleState.CHECKPOINTED,
            now=T0 + timedelta(seconds=1),
            lease_seconds=5,
        )
        # Snapshot the scalar: later repository reads refresh the same ORM identity in this session.
        old_checkpoint_revision = int(old_progress.execution.checkpoint_revision)
        assert json.loads(old_progress.execution.checkpoint_json)["plan_ref"] == f"agentic-plan:{OLD_PLAN_ID}"

        _append_human_refresh_history(Session, run.id)

        expired_at = T0 + timedelta(seconds=7)
        with pytest.raises(WorkerLeaseExpired):
            service.acquire(run_id=run.id, now=expired_at, lease_seconds=5)
        decision = service.classify_and_stall(
            run_id=run.id,
            evidence=WorkerStallEvidence(process_lost=True),
            blocker_code="AGENTIC_PROCESS_LOSS",
            now=expired_at,
        )
        assert decision.action.value == "REASSIGN"
        service.begin_recovery(run_id=run.id, now=expired_at + timedelta(seconds=1))
        fresh_lease = service.reassign(
            run_id=run.id,
            now=expired_at + timedelta(seconds=2),
            lease_seconds=30,
        )
        assert fresh_lease.generation == old_lease.generation + 1

        rebound = service.checkpoint(
            fresh_lease,
            _checkpoint(run, FRESH_PLAN_ID, step="AGENT_DISPATCH"),
            authoritative_source_lineage_ref=LINEAGE,
            state=WorkerLifecycleState.PROGRESSING,
            now=expired_at + timedelta(seconds=3),
        )
        rebound_payload = json.loads(rebound.execution.checkpoint_json)
        assert rebound_payload["plan_ref"] == f"agentic-plan:{FRESH_PLAN_ID}"
        assert rebound.execution.checkpoint_revision == old_checkpoint_revision + 1
        assert rebound.execution.source_lineage_ref == LINEAGE
        assert rebound.execution.last_known_good_lineage_ref == LINEAGE

        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            service.checkpoint(
                fresh_lease,
                _checkpoint(run, OTHER_PLAN_ID, step="AGENT_DISPATCH"),
                authoritative_source_lineage_ref=LINEAGE,
                state=WorkerLifecycleState.PROGRESSING,
                now=expired_at + timedelta(seconds=4),
            )
    finally:
        session.close()


def test_refresh_must_be_latest_exact_plan_pair(tmp_path) -> None:
    Session = _session_factory(tmp_path)
    run = _insert_run(Session)
    session, service = _service(Session)
    try:
        lease = service.acquire(run_id=run.id, now=T0)
        service.checkpoint(
            lease,
            _checkpoint(run, OLD_PLAN_ID, step="AGENT_PROPOSAL"),
            authoritative_source_lineage_ref=LINEAGE,
            now=T0 + timedelta(seconds=1),
        )
        _append_human_refresh_history(Session, run.id)
        _append_plan_attempt(
            Session,
            run.id,
            attempt_number=4,
            status="PASSED",
            evidence={
                "decision_kind": "SERVER_OWNED_AGENTIC_PLAN",
                "team_plan_id": OTHER_PLAN_ID,
            },
            at=T0 + timedelta(seconds=8),
        )

        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            service.checkpoint(
                lease,
                _checkpoint(run, OTHER_PLAN_ID, step="AGENT_DISPATCH"),
                authoritative_source_lineage_ref=LINEAGE,
                now=T0 + timedelta(seconds=9),
            )
    finally:
        session.close()
