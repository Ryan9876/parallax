from __future__ import annotations

import json

import pytest

from parallax_api.code.agent_protocol import (
    AgentEvidenceReference,
    AgentIdentity,
    AgentLifecycleStatus,
    AgentResult,
    EvidenceKind,
    MetricAvailability,
    MetricName,
    MetricObservation,
)
from parallax_api.code.agent_team_orchestration import (
    AdmittedAgent,
    AdmittedRoster,
    OrchestrationDisposition,
    OrchestrationError,
    OrchestrationLimits,
    PlanContextReason,
    WorkGraph,
    WorkUnit,
    admit_assignment_result,
    build_team_plan,
    create_agent_task_request,
    evaluate_orchestration_bounds,
    observe_admitted_result,
    reassign_assignment,
    safe_orchestration_json,
    schedule_team_plan,
    verify_plan_context,
)
from parallax_api.code.worker_recovery import (
    RecoveryAction,
    StallClassification,
    WorkerHealthSnapshot,
    WorkerLifecycleState,
)

PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
POLICY = "b" * 64


def agent(name: str, capabilities=("source-evidence",)) -> AgentIdentity:
    return AgentIdentity(
        agent_id=name,
        agent_version="1.0.0",
        adapter_id=f"{name}-adapter",
        adapter_version="1.0.0",
        provider_kind="reference",
        declared_work_kinds=("implementation",),
        declared_capabilities=tuple(capabilities),
    )


def admitted(identity: AgentIdentity, capabilities=None) -> AdmittedAgent:
    return AdmittedAgent(
        identity=identity,
        admitted_work_kinds=("implementation",),
        admitted_capabilities=identity.declared_capabilities if capabilities is None else tuple(capabilities),
    )


def roster() -> AdmittedRoster:
    return AdmittedRoster((admitted(agent("agent-a")), admitted(agent("agent-b"))))


def graph(*, serial=False, overlap=False, mutation=False) -> WorkGraph:
    return WorkGraph(
        approved_acceptance_ids=("AC-01", "AC-02"),
        units=(
            WorkUnit(
                "api",
                "implementation",
                ("AC-01",),
                required_capabilities=("source-evidence",),
                coordination_domains=("shared",) if overlap else ("backend",),
                requires_canonical_mutation=mutation,
                context_refs=(AgentEvidenceReference(EvidenceKind.SOURCE, "source:api"),),
            ),
            WorkUnit(
                "ui",
                "implementation",
                ("AC-02",),
                dependencies=("api",) if serial else (),
                required_capabilities=("source-evidence",),
                coordination_domains=("shared",) if overlap else ("frontend",),
                requires_canonical_mutation=mutation,
            ),
        ),
    )


def ready_plan(*, serial=False, overlap=False, mutation=False, selected_roster=None, limits=None):
    decision = build_team_plan(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        graph=graph(serial=serial, overlap=overlap, mutation=mutation),
        roster=selected_roster or roster(),
        policy_digest=POLICY,
        limits=limits,
    )
    assert decision.disposition is OrchestrationDisposition.READY
    assert decision.plan is not None
    return decision.plan


def result_for(task) -> AgentResult:
    return AgentResult(
        binding=task.binding,
        agent=task.agent,
        status=AgentLifecycleStatus.COMPLETED,
        reason_code=None,
        summary="bounded implementation evidence completed",
        claimed_acceptance_ids=task.binding.acceptance_ids,
        evidence_refs=(AgentEvidenceReference(EvidenceKind.ARTIFACT, "artifact:s2-result"),),
        metrics=(MetricObservation(MetricName.COST, MetricAvailability.UNAVAILABLE, "s2-adapter"),),
    )


def worker(*, execution_id="worker:s2", generation=4, action=RecoveryAction.REASSIGN, human_required=False):
    return WorkerHealthSnapshot(
        execution_id=execution_id,
        project_id=PROJECT,
        run_id=RUN,
        state=WorkerLifecycleState.STALLED,
        lease_status="ACTIVE",
        lease_generation=generation,
        current_step="IMPLEMENT",
        source_lineage_ref=None,
        last_known_good_lineage_ref=None,
        checkpoint_revision=3,
        last_meaningful_progress_at=None,
        retry_count=1,
        no_progress_count=1,
        oscillation_count=0,
        stall_classification=StallClassification.PROCESS_LOSS,
        blocker_code="PROCESS_LOSS",
        dependencies=(),
        next_recovery_action=action,
        human_required=human_required,
    )


def test_exact_identity_and_replay_are_deterministic():
    first = ready_plan()
    second = ready_plan()
    assert first.plan_id == second.plan_id
    assert first.identity.project_id == PROJECT
    assert first.identity.run_id == RUN
    assert first.identity.work_specification_id == SPEC
    assert first.identity.work_specification_digest == SPEC_DIGEST
    assert first.identity.policy_digest == POLICY
    assert first.identity.work_graph_digest == first.graph.digest
    assert first.identity.roster_digest == first.roster.digest
    assert schedule_team_plan(first).as_dict() == schedule_team_plan(second).as_dict()


def test_context_drift_fails_closed_by_exact_reason():
    plan = ready_plan()
    kwargs = dict(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=("AC-01", "AC-02"),
        policy_digest=POLICY,
        graph=plan.graph,
        roster=plan.roster,
    )
    assert verify_plan_context(plan, **kwargs).matched
    assert verify_plan_context(plan, **{**kwargs, "policy_digest": "c" * 64}).reason is PlanContextReason.POLICY_DRIFT
    assert verify_plan_context(plan, **{**kwargs, "project_id": "44444444-4444-4444-8444-444444444444"}).reason is PlanContextReason.PROJECT_MISMATCH
    changed = WorkGraph(plan.graph.approved_acceptance_ids, (plan.graph.units[0], WorkUnit("web", "implementation", ("AC-02",), required_capabilities=("source-evidence",), coordination_domains=("frontend",))))
    assert verify_plan_context(plan, **{**kwargs, "graph": changed}).reason is PlanContextReason.WORK_GRAPH_DRIFT


def test_server_admission_cannot_invent_capability_and_both_sides_are_required():
    identity = agent("agent-a", capabilities=("source-evidence",))
    with pytest.raises(OrchestrationError):
        admitted(identity, capabilities=("shell",))
    limited = AdmittedRoster((admitted(identity, capabilities=()),))
    decision = build_team_plan(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        graph=graph(serial=True),
        roster=limited,
        policy_digest=POLICY,
    )
    assert decision.disposition is OrchestrationDisposition.HUMAN_REQUIRED
    assert decision.reason_code == "NO_COMPATIBLE_ADMITTED_AGENT"


def test_smallest_adequate_team_is_one_for_serial_and_two_for_parallel():
    serial_plan = ready_plan(serial=True)
    assert len(serial_plan.selected_agent_digests) == 1
    parallel_plan = ready_plan()
    assert len(parallel_plan.selected_agent_digests) == 2
    ready = schedule_team_plan(parallel_plan).ready
    assert len(ready) == 2
    assert len({item.agent_identity_digest for item in ready}) == 2


def test_overlap_unknown_domain_and_mutation_serialize_parallel_work():
    overlap_plan = ready_plan(overlap=True)
    assert len(overlap_plan.selected_agent_digests) == 1
    mutation_plan = ready_plan(mutation=True)
    assert len(mutation_plan.selected_agent_digests) == 1
    unknown = WorkGraph(
        ("AC-01", "AC-02"),
        (WorkUnit("a1", "implementation", ("AC-01",), required_capabilities=("source-evidence",)), WorkUnit("b1", "implementation", ("AC-02",), required_capabilities=("source-evidence",))),
    )
    decision = build_team_plan(project_id=PROJECT, run_id=RUN, work_specification_id=SPEC, work_specification_revision=2, work_specification_digest=SPEC_DIGEST, graph=unknown, roster=roster(), policy_digest=POLICY)
    assert decision.plan is not None and len(decision.plan.selected_agent_digests) == 1


def test_graph_rejects_cycles_missing_dependencies_duplicates_and_acceptance_drift():
    with pytest.raises(OrchestrationError):
        WorkGraph(("AC-01",), (WorkUnit("a1", "implementation", ("AC-01",), dependencies=("b1",)),))
    with pytest.raises(OrchestrationError):
        WorkGraph(("AC-01", "AC-02"), (WorkUnit("a1", "implementation", ("AC-01",), dependencies=("b1",)), WorkUnit("b1", "implementation", ("AC-02",), dependencies=("a1",))))
    with pytest.raises(OrchestrationError):
        WorkGraph(("AC-01",), (WorkUnit("a1", "implementation", ("AC-01",)), WorkUnit("a1", "implementation", ("AC-01",))))
    with pytest.raises(OrchestrationError):
        WorkGraph(("AC-01",), (WorkUnit("a1", "implementation", ("AC-02",)),))
    with pytest.raises(OrchestrationError):
        WorkGraph(("AC-01",), (WorkUnit("a1", "implementation", ("AC-01",)), WorkUnit("b1", "implementation", ("AC-01",))))


def test_dependency_schedule_waits_then_becomes_ready_without_duplicate_identity():
    plan = ready_plan(serial=True)
    first = schedule_team_plan(plan)
    api = next(item for item in first.assignments if item.work_unit_id == "api")
    ui = next(item for item in first.assignments if item.work_unit_id == "ui")
    assert api.disposition is OrchestrationDisposition.READY
    assert ui.disposition is OrchestrationDisposition.WAITING_DEPENDENCY
    second = schedule_team_plan(plan, completed_work_units=("api",))
    ui2 = next(item for item in second.assignments if item.work_unit_id == "ui")
    assert ui2.disposition is OrchestrationDisposition.READY
    assert ui2.plan_id == ui.plan_id
    assert schedule_team_plan(plan, completed_work_units=("api",)).as_dict() == second.as_dict()


def test_s1_task_binding_and_result_admission_preserve_non_authority():
    plan = ready_plan(serial=True)
    assignment = schedule_team_plan(plan).ready[0]
    task = create_agent_task_request(plan, assignment)
    assert task.binding.project_id == PROJECT
    assert task.binding.run_id == RUN
    assert task.binding.work_specification_id == SPEC
    assert task.binding.attempt_number == assignment.generation
    output = result_for(task)
    admitted_result = admit_assignment_result(plan, assignment, expected_task=task, result=output, current_generation=assignment.generation)
    assert admitted_result.admitted
    observation = observe_admitted_result(plan, assignment, admission=admitted_result, result=output)
    payload = observation.as_dict()
    assert payload["quality_is_authoritative"] is False
    assert payload["cost_is_inferred"] is False
    assert payload["grants_authority"] is False


def test_stale_generation_late_result_and_duplicate_terminal_fail_closed():
    plan = ready_plan(serial=True)
    assignment = schedule_team_plan(plan).ready[0]
    task = create_agent_task_request(plan, assignment)
    output = result_for(task)
    stale = admit_assignment_result(plan, assignment, expected_task=task, result=output, current_generation=2)
    assert not stale.admitted and stale.reason_code == "STALE_ASSIGNMENT_GENERATION"
    revoked = admit_assignment_result(plan, assignment, expected_task=task, result=output, current_generation=1, revoked=True)
    assert not revoked.admitted and revoked.reason_code == "S1_REVOKED"
    duplicate = admit_assignment_result(plan, assignment, expected_task=task, result=output, current_generation=1, accepted_terminal_digest=output.digest)
    assert not duplicate.admitted and duplicate.duplicate and duplicate.reason_code == "S1_DUPLICATE"


def test_reassignment_requires_current_authoritative_worker_reassign_evidence():
    plan = ready_plan(serial=True)
    current = schedule_team_plan(plan).ready[0]
    denied = reassign_assignment(plan, current, worker_health=worker(action=RecoveryAction.RETRY), expected_worker_execution_id="worker:s2", expected_worker_lease_generation=4, reassignment_count=0)
    assert denied.disposition is OrchestrationDisposition.BLOCKED
    stale = reassign_assignment(plan, current, worker_health=worker(generation=5), expected_worker_execution_id="worker:s2", expected_worker_lease_generation=4, reassignment_count=0)
    assert stale.reason_code == "STALE_WORKER_GENERATION"
    approved = reassign_assignment(plan, current, worker_health=worker(), expected_worker_execution_id="worker:s2", expected_worker_lease_generation=4, reassignment_count=0)
    assert approved.disposition is OrchestrationDisposition.REASSIGNED
    assert approved.assignment is not None
    assert approved.assignment.generation == current.generation + 1
    assert approved.assignment.agent_identity_digest != current.agent_identity_digest


def test_reassignment_and_no_progress_bounds_terminate_human_required():
    limits = OrchestrationLimits(max_team_size=2, max_concurrency=2, max_reassignments_per_work_unit=1, max_replans=2, max_no_progress=2)
    plan = ready_plan(serial=True, limits=limits)
    current = schedule_team_plan(plan).ready[0]
    exhausted = reassign_assignment(plan, current, worker_health=worker(), expected_worker_execution_id="worker:s2", expected_worker_lease_generation=4, reassignment_count=1)
    assert exhausted.disposition is OrchestrationDisposition.HUMAN_REQUIRED
    assert not evaluate_orchestration_bounds(plan, replan_count=2, no_progress_count=0).allowed
    assert not evaluate_orchestration_bounds(plan, replan_count=0, no_progress_count=2).allowed


def test_safe_serialization_contains_no_authority_or_raw_provider_material():
    plan = ready_plan()
    serialized = safe_orchestration_json(plan)
    parsed = json.loads(serialized)
    assert parsed["accepts_source_lineage"] is False
    assert parsed["writes_canonical_source"] is False
    assert parsed["transitions_engineering_run"] is False
    assert parsed["grants_tools_or_provider_authority"] is False
    assert parsed["completes_review"] is False
    lowered = serialized.lower()
    for token in ("authorization:", "bearer ", "password=", "token=", "https://", "http://", "raw_provider_payload", "hidden_reasoning"):
        assert token not in lowered


def test_process_recreation_from_same_immutable_values_is_identical():
    first = ready_plan()
    recreated_graph = graph()
    recreated_roster = roster()
    second = build_team_plan(project_id=PROJECT, run_id=RUN, work_specification_id=SPEC, work_specification_revision=2, work_specification_digest=SPEC_DIGEST, graph=recreated_graph, roster=recreated_roster, policy_digest=POLICY).plan
    assert second is not None
    assert first.plan_id == second.plan_id
    assert schedule_team_plan(first).as_dict() == schedule_team_plan(second).as_dict()


def _priority_admitted(name: str, priority: int) -> AdmittedAgent:
    identity = agent(name)
    return AdmittedAgent(
        identity=identity,
        admitted_work_kinds=("implementation",),
        admitted_capabilities=identity.declared_capabilities,
        selection_priority=priority,
    )


def test_server_owned_selection_priority_controls_smallest_team_order():
    priority_roster = AdmittedRoster(
        (
            _priority_admitted("priority-sol", 2),
            _priority_admitted("priority-luna", 0),
            _priority_admitted("priority-terra", 1),
        )
    )
    assert tuple(item.identity.agent_id for item in priority_roster.entries) == (
        "priority-luna",
        "priority-terra",
        "priority-sol",
    )

    serial_plan = ready_plan(serial=True, selected_roster=priority_roster)
    assert tuple(serial_plan.roster.get(item).identity.agent_id for item in serial_plan.selected_agent_digests) == (
        "priority-luna",
    )
    assert serial_plan.roster.get(schedule_team_plan(serial_plan).ready[0].agent_identity_digest).identity.agent_id == "priority-luna"

    parallel_plan = ready_plan(selected_roster=priority_roster)
    assert tuple(parallel_plan.roster.get(item).identity.agent_id for item in parallel_plan.selected_agent_digests) == (
        "priority-luna",
        "priority-terra",
    )
    assert "priority-sol" not in {
        parallel_plan.roster.get(item).identity.agent_id for item in parallel_plan.selected_agent_digests
    }


def test_priority_order_is_deterministic_evidence_and_digest_ties_remain_canonical():
    first = AdmittedRoster(
        (
            _priority_admitted("priority-sol", 2),
            _priority_admitted("priority-luna", 0),
            _priority_admitted("priority-terra", 1),
        )
    )
    second = AdmittedRoster(tuple(reversed(first.entries)))
    assert first.digest == second.digest
    assert ready_plan(selected_roster=first).plan_id == ready_plan(selected_roster=second).plan_id

    changed = AdmittedRoster(
        (
            _priority_admitted("priority-sol", 2),
            _priority_admitted("priority-luna", 3),
            _priority_admitted("priority-terra", 1),
        )
    )
    assert changed.digest != first.digest

    tied = AdmittedRoster(
        (
            _priority_admitted("tie-c", 5),
            _priority_admitted("tie-a", 5),
            _priority_admitted("tie-b", 5),
        )
    )
    assert tuple(item.identity_digest for item in tied.entries) == tuple(
        sorted(item.identity_digest for item in tied.entries)
    )
