from __future__ import annotations

from hashlib import sha256

from parallax_api.code.agent_protocol import AgentIdentity
from parallax_api.code.agent_team_orchestration import (
    AdmittedAgent,
    AdmittedRoster,
    OrchestrationDisposition,
    OrchestrationLimits,
    WorkGraph,
    WorkUnit,
    build_team_plan,
    schedule_team_plan,
)
from parallax_api.code.agentic_candidate_recovery import (
    CANDIDATE_VALIDATION_REPAIR,
    MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
    candidate_recovery_assignment,
    validator_repair_assignment,
)


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _identity(name: str) -> AgentIdentity:
    return AgentIdentity(
        agent_id=name,
        agent_version="1.0.0",
        adapter_id="protected-implementation-generation",
        adapter_version="1.0.0",
        provider_kind="openai",
        declared_work_kinds=("implementation",),
        declared_capabilities=("bounded-source-evidence",),
        model_runtime_label=name,
    )


def _plan():
    agents = tuple(
        AdmittedAgent(
            _identity(name),
            admitted_work_kinds=("implementation",),
            admitted_capabilities=("bounded-source-evidence",),
            selection_priority=priority,
        )
        for priority, name in enumerate(("model-luna", "model-terra", "model-sol"))
    )
    graph = WorkGraph(
        approved_acceptance_ids=("AC-01",),
        units=(
            WorkUnit(
                unit_id="implementation",
                work_kind="implementation",
                acceptance_ids=("AC-01",),
                required_capabilities=("bounded-source-evidence",),
                coordination_domains=("source",),
            ),
        ),
    )
    decision = build_team_plan(
        project_id="11111111-1111-1111-1111-111111111111",
        run_id="22222222-2222-2222-2222-222222222222",
        work_specification_id="33333333-3333-3333-3333-333333333333",
        work_specification_revision=1,
        work_specification_digest=_digest("spec"),
        graph=graph,
        roster=AdmittedRoster(agents),
        policy_digest=_digest("policy"),
        limits=OrchestrationLimits(
            max_team_size=3,
            max_concurrency=3,
            max_reassignments_per_work_unit=2,
            max_replans=3,
            max_no_progress=3,
        ),
    )
    assert decision.plan is not None
    return decision.plan


def _model_label(plan, digest: str) -> str:
    value = plan.roster.get(digest).identity.model_runtime_label
    assert value is not None
    return value


def test_candidate_rejection_reassigns_to_next_admitted_agent_with_fresh_identity():
    plan = _plan()
    original = schedule_team_plan(plan).ready[0]
    assert original.agent_identity_digest is not None
    assert _model_label(plan, original.agent_identity_digest) == "model-luna"

    retry = candidate_recovery_assignment(
        plan,
        original,
        attempted_agent_digests=(original.agent_identity_digest,),
        rejection_count=1,
    )

    assert retry is not None
    assert retry.disposition is OrchestrationDisposition.REASSIGNED
    assert retry.reason_code == "CANDIDATE_GENERATION_RETRY"
    assert retry.agent_identity_digest != original.agent_identity_digest
    assert _model_label(plan, retry.agent_identity_digest) == "model-terra"
    assert retry.agent_identity_digest in plan.unit_plan("implementation").eligible_agent_digests
    assert retry.generation == original.generation + 1
    assert retry.operation_id != original.operation_id
    assert retry.request_id != original.request_id
    assert retry.attempt_id != original.attempt_id
    assert retry.dependency_digest == original.dependency_digest


def test_candidate_recovery_is_deterministic_and_stops_at_existing_bound():
    plan = _plan()
    original = schedule_team_plan(plan).ready[0]
    assert original.agent_identity_digest is not None

    retry1 = candidate_recovery_assignment(
        plan,
        original,
        attempted_agent_digests=(original.agent_identity_digest,),
        rejection_count=1,
    )
    assert retry1 is not None and retry1.agent_identity_digest is not None
    retry2 = candidate_recovery_assignment(
        plan,
        retry1,
        attempted_agent_digests=(original.agent_identity_digest, retry1.agent_identity_digest),
        rejection_count=2,
    )
    assert retry2 is not None
    assert retry2.agent_identity_digest is not None
    assert _model_label(plan, retry2.agent_identity_digest) == "model-sol"
    assert retry2.agent_identity_digest not in {
        original.agent_identity_digest,
        retry1.agent_identity_digest,
    }

    exhausted = candidate_recovery_assignment(
        plan,
        retry2,
        attempted_agent_digests=(
            original.agent_identity_digest,
            retry1.agent_identity_digest,
            retry2.agent_identity_digest or "",
        ),
        rejection_count=3,
    )
    assert exhausted is None


def test_final_validator_repair_reuses_most_recent_rejected_admitted_agent_once():
    plan = _plan()
    original = schedule_team_plan(plan).ready[0]
    assert original.agent_identity_digest is not None

    retry1 = candidate_recovery_assignment(
        plan,
        original,
        attempted_agent_digests=(original.agent_identity_digest,),
        rejection_count=1,
    )
    assert retry1 is not None and retry1.agent_identity_digest is not None
    retry2 = candidate_recovery_assignment(
        plan,
        retry1,
        attempted_agent_digests=(original.agent_identity_digest, retry1.agent_identity_digest),
        rejection_count=2,
    )
    assert retry2 is not None and retry2.agent_identity_digest is not None

    distinct_exhausted = candidate_recovery_assignment(
        plan,
        retry2,
        attempted_agent_digests=(
            original.agent_identity_digest,
            retry1.agent_identity_digest,
            retry2.agent_identity_digest,
        ),
        rejection_count=3,
    )
    assert distinct_exhausted is None

    repair = validator_repair_assignment(
        plan,
        retry2,
        validator_rejected_agent_digests=(
            retry1.agent_identity_digest,
            retry2.agent_identity_digest,
        ),
        repair_count=0,
    )
    assert repair is not None
    assert repair.disposition is OrchestrationDisposition.REASSIGNED
    assert repair.reason_code == CANDIDATE_VALIDATION_REPAIR
    assert repair.agent_identity_digest == retry2.agent_identity_digest
    assert _model_label(plan, repair.agent_identity_digest) == "model-sol"
    assert repair.generation == retry2.generation + 1
    assert repair.operation_id != retry2.operation_id
    assert repair.request_id != retry2.request_id
    assert repair.attempt_id != retry2.attempt_id
    assert MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT == 1

    assert validator_repair_assignment(
        plan,
        repair,
        validator_rejected_agent_digests=(retry2.agent_identity_digest,),
        repair_count=1,
    ) is None


def test_final_validator_repair_is_not_available_for_provider_only_failures():
    plan = _plan()
    original = schedule_team_plan(plan).ready[0]
    assert original.agent_identity_digest is not None
    assert validator_repair_assignment(
        plan,
        original,
        validator_rejected_agent_digests=(),
        repair_count=0,
    ) is None


def test_final_validator_repair_uses_last_validator_rejection_not_last_provider_failure():
    plan = _plan()
    original = schedule_team_plan(plan).ready[0]
    assert original.agent_identity_digest is not None
    retry1 = candidate_recovery_assignment(
        plan,
        original,
        attempted_agent_digests=(original.agent_identity_digest,),
        rejection_count=1,
    )
    assert retry1 is not None and retry1.agent_identity_digest is not None
    retry2 = candidate_recovery_assignment(
        plan,
        retry1,
        attempted_agent_digests=(original.agent_identity_digest, retry1.agent_identity_digest),
        rejection_count=2,
    )
    assert retry2 is not None and retry2.agent_identity_digest is not None

    repair = validator_repair_assignment(
        plan,
        retry2,
        validator_rejected_agent_digests=(retry1.agent_identity_digest,),
        repair_count=0,
    )
    assert repair is not None
    assert repair.agent_identity_digest == retry1.agent_identity_digest
    assert _model_label(plan, repair.agent_identity_digest) == "model-terra"


def test_final_validator_repair_fails_closed_for_non_admitted_identity():
    import pytest
    from parallax_api.code.agentic_runtime import AgenticRuntimeError

    plan = _plan()
    original = schedule_team_plan(plan).ready[0]
    with pytest.raises(AgenticRuntimeError):
        validator_repair_assignment(
            plan,
            original,
            validator_rejected_agent_digests=(_digest("not-admitted"),),
            repair_count=0,
        )


def test_validator_repair_tracking_is_scoped_inside_each_scheduled_work_unit():
    import inspect
    from parallax_api.code.agentic_candidate_recovery import ResilientLiveAgenticControlPlane

    # Repair accounting must reset before each work-unit candidate loop.
    source = inspect.getsource(ResilientLiveAgenticControlPlane._proposal_for_plan)
    unit_scope = source.index("for scheduled_assignment in ready:")
    rejected_scope = source.index("validator_rejected_agent_digests: list[str] = []")
    repair_scope = source.index("validator_repair_count = 0")
    loop_scope = source.index("while True:")
    assert unit_scope < rejected_scope < loop_scope
    assert unit_scope < repair_scope < loop_scope
