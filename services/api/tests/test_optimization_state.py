from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.optimization_controller import (
    CriticalPathScheduler,
    DependencyGraph,
    DependencyNode,
    EngineeringAttemptOptimizationStateStore,
    OptimizationNodeKind,
    OptimizationNodeState,
    OptimizationState,
    OptimizationStateConflict,
)
from parallax_api.db import Base, make_engine
from parallax_api.models import EngineeringRun
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.worker_executions import EngineeringWorkerExecution

T0 = datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)


def _db_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'optimization.db'}")
    assert EngineeringWorkerExecution.__tablename__ == "engineering_worker_executions"
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _insert_run(Session):
    run = EngineeringRun(
        id=str(uuid4()), conversation_id=str(uuid4()), spec_id="P2-V0.16.4", project_id=str(uuid4()),
        work_specification_id=str(uuid4()), work_specification_revision=4, work_specification_digest="d" * 64,
        state="IMPLEMENT", revision=0, workspace_ref=None,
    )
    with Session() as session:
        session.add(run)
        session.commit()
    return run


def _graph(project_id: str) -> DependencyGraph:
    return DependencyGraph(
        project_id=project_id, revision=7,
        nodes=(
            DependencyNode("contract:worker", OptimizationNodeKind.CONTRACT, OptimizationNodeState.PASSED),
            DependencyNode(
                "ws:critical", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY,
                dependencies=("contract:worker",), remaining_cost=4, acceptance_refs=("AC-01", "AC-02"),
            ),
        ),
    )


def test_optimization_graph_persists_recreates_and_cas_updates_without_run_state_mutation(tmp_path) -> None:
    Session = _db_context(tmp_path)
    run = _insert_run(Session)
    graph = _graph(run.project_id)

    first_session = Session()
    try:
        repository = EngineeringRunRepository(first_session)
        bound_run = repository.get(run.id)
        assert bound_run is not None
        store = EngineeringAttemptOptimizationStateStore(repository)
        initial = OptimizationState(
            session_id="session:optimization", project_id=run.project_id, run_id=run.id,
            work_specification_id=run.work_specification_id, work_specification_revision=run.work_specification_revision,
            work_specification_digest=run.work_specification_digest, graph=graph,
            evidence_refs=("spec:P2-V0.16.4",), updated_at=T0,
        )
        saved = store.save(run=bound_run, state=initial, expected_revision=0)
        assert saved.revision == 1 and bound_run.state == "IMPLEMENT"
    finally:
        first_session.close()

    recreated_session = Session()
    try:
        repository = EngineeringRunRepository(recreated_session)
        bound_run = repository.get(run.id)
        assert bound_run is not None
        store = EngineeringAttemptOptimizationStateStore(repository)
        recreated = store.load(run_id=run.id, session_id="session:optimization")
        assert recreated is not None and recreated.graph.digest == graph.digest
        assert CriticalPathScheduler().rank(recreated.graph) == CriticalPathScheduler().rank(graph)

        updated_graph = replace(recreated.graph, revision=recreated.graph.revision + 1)
        updated = replace(recreated, graph=updated_graph, updated_at=T0 + timedelta(seconds=1))
        saved2 = store.save(run=bound_run, state=updated, expected_revision=1)
        assert saved2.revision == 2 and bound_run.state == "IMPLEMENT"
        with pytest.raises(OptimizationStateConflict, match="compare-and-swap"):
            store.save(run=bound_run, state=recreated, expected_revision=1)
    finally:
        recreated_session.close()
