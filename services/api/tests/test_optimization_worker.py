from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.optimization_controller import (
    CancellationAction,
    DependencyGraph,
    DependencyNode,
    OptimizationNodeKind,
    OptimizationNodeState,
    OptimizationWorkerConflict,
    PathOwnership,
    SafeBoundary,
    apply_work_steal,
    cancellation_decision,
    propose_work_steal,
)
from parallax_api.code.worker_recovery import WorkerStallEvidence
from parallax_api.code.worker_service import WorkerRecoveryService
from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringRun
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository


T0 = datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)


def _db_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'optimization-worker.db'}")
    assert EngineeringWorkerExecution.__tablename__ == "engineering_worker_executions"
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _insert_run(Session):
    run = EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.16.4",
        project_id=str(uuid4()),
        work_specification_id=str(uuid4()),
        work_specification_revision=4,
        work_specification_digest="d" * 64,
        state="IMPLEMENT",
        revision=0,
        workspace_ref=None,
    )
    with Session() as session:
        session.add(run)
        session.commit()
    return run


def _graph(*, ready: bool = True, revision: int = 1) -> DependencyGraph:
    return DependencyGraph(
        project_id="project:optimization",
        revision=revision,
        nodes=(
            DependencyNode(
                "contract:worker",
                OptimizationNodeKind.CONTRACT,
                OptimizationNodeState.PASSED if ready else OptimizationNodeState.BLOCKED,
                remaining_cost=0,
            ),
            DependencyNode(
                "ws:critical",
                OptimizationNodeKind.WORKSTREAM,
                OptimizationNodeState.READY,
                dependencies=("contract:worker",),
                remaining_cost=4,
                acceptance_refs=("AC-03",),
            ),
        ),
    )


def _recovering_service(Session, run):
    session = Session()
    service = WorkerRecoveryService(WorkerExecutionRepository(session), EngineeringRunRepository(session))
    lease = service.acquire(run_id=run.id, now=T0, lease_seconds=30)
    service.classify_and_stall(
        run_id=run.id,
        evidence=WorkerStallEvidence(process_lost=True),
        now=T0 + timedelta(seconds=31),
    )
    service.begin_recovery(run_id=run.id, now=T0 + timedelta(seconds=32))
    return session, service, lease, service.health(run_id=run.id, now=T0 + timedelta(seconds=32))


def test_work_steal_reuses_worker_recovery_generation_and_rejects_conflicts(tmp_path) -> None:
    Session = _db_context(tmp_path)
    run = _insert_run(Session)
    session, service, lease, health = _recovering_service(Session, run)
    graph = _graph()
    try:
        assert health.lease_status == "UNOWNED"
        conflict = propose_work_steal(
            graph=graph,
            run_id=run.id,
            node_id="ws:critical",
            worker_health=health,
            requested_paths=("services/api/parallax_api/code",),
            ownership=(PathOwnership("services/api", "other-execution"),),
            target_capability="python:api",
            safe_boundary=SafeBoundary.BEFORE_MUTATION,
        )
        assert conflict.eligible is False
        assert conflict.reason == "PATH_OWNERSHIP_CONFLICT"

        proposal = propose_work_steal(
            graph=graph,
            run_id=run.id,
            node_id="ws:critical",
            worker_health=health,
            requested_paths=("services/api/parallax_api/code",),
            ownership=(),
            target_capability="python:api",
            safe_boundary=SafeBoundary.BEFORE_MUTATION,
        )
        assert proposal.graph_digest == graph.digest
        new_lease = apply_work_steal(
            service,
            proposal,
            current_graph=graph,
            now=T0 + timedelta(seconds=33),
            lease_seconds=30,
        )
        assert new_lease.execution_id == lease.execution_id
        assert new_lease.generation == 2

        with pytest.raises(OptimizationWorkerConflict, match="stale"):
            apply_work_steal(
                service,
                proposal,
                current_graph=graph,
                now=T0 + timedelta(seconds=34),
                lease_seconds=30,
            )
    finally:
        session.close()


def test_work_steal_requires_dependency_ready_work_and_current_graph(tmp_path) -> None:
    Session = _db_context(tmp_path)
    run = _insert_run(Session)
    session, service, _, health = _recovering_service(Session, run)
    try:
        blocked_graph = _graph(ready=False)
        blocked = propose_work_steal(
            graph=blocked_graph,
            run_id=run.id,
            node_id="ws:critical",
            worker_health=health,
            requested_paths=("services/api",),
            ownership=(),
            target_capability="python:api",
            safe_boundary=SafeBoundary.BEFORE_MUTATION,
        )
        assert blocked.eligible is False
        assert blocked.reason == "WORK_NOT_READY"

        graph = _graph()
        proposal = propose_work_steal(
            graph=graph,
            run_id=run.id,
            node_id="ws:critical",
            worker_health=health,
            requested_paths=("services/api",),
            ownership=(),
            target_capability="python:api",
            safe_boundary=SafeBoundary.BEFORE_MUTATION,
        )
        stale_graph = replace(graph, revision=graph.revision + 1)
        with pytest.raises(OptimizationWorkerConflict, match="graph state is stale"):
            apply_work_steal(service, proposal, current_graph=stale_graph, now=T0 + timedelta(seconds=33))
    finally:
        session.close()


def test_work_steal_and_cancellation_fail_closed_during_protected_operation(tmp_path) -> None:
    Session = _db_context(tmp_path)
    run = _insert_run(Session)
    session = Session()
    try:
        service = WorkerRecoveryService(WorkerExecutionRepository(session), EngineeringRunRepository(session))
        service.acquire(run_id=run.id, now=T0, lease_seconds=30)
        active = service.health(run_id=run.id, now=T0 + timedelta(seconds=1))
        denied = propose_work_steal(
            graph=_graph(),
            run_id=run.id,
            node_id="ws:critical",
            worker_health=active,
            requested_paths=("services/api",),
            ownership=(),
            target_capability="python:api",
            safe_boundary=SafeBoundary.UNSAFE,
            protected_operation_in_flight=True,
        )
        assert denied.eligible is False
        with pytest.raises(OptimizationWorkerConflict):
            apply_work_steal(service, denied, current_graph=_graph(), now=T0 + timedelta(seconds=2))

        wait = cancellation_decision(
            boundary=SafeBoundary.AFTER_RECORDED_SIDE_EFFECT,
            protected_operation_in_flight=True,
        )
        assert wait.action is CancellationAction.WAIT
        assert wait.allowed is False
        safe = cancellation_decision(boundary=SafeBoundary.AFTER_ACCEPTED_VALIDATION, supersede=True)
        assert safe.action is CancellationAction.SUPERSEDE_AT_CHECKPOINT
        assert safe.allowed is True
    finally:
        session.close()
