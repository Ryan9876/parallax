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
from parallax_api.code.agentic_candidate_recovery import candidate_recovery_assignment


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
