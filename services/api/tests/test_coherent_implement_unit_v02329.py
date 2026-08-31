from __future__ import annotations

from parallax_api.code.agent_team_orchestration import (
    OrchestrationDisposition,
    build_team_plan,
    schedule_team_plan,
)
from parallax_api.code.agentic_candidate_recovery import (
    MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
    candidate_recovery_assignment,
)
from parallax_api.code.agentic_runtime import AgenticControlPlane, _MODEL_ORDER
from parallax_api.intelligence.dspy_programs import (
    _HOSTED_MODEL_NUM_RETRIES,
    _HOSTED_MODEL_TIMEOUT_SECONDS,
)


def _control() -> AgenticControlPlane:
    return AgenticControlPlane(None, None)


def _multi_domain_acceptance() -> tuple[dict[str, str], ...]:
    return (
        {"id": "AC-01", "text": "Update the client button and browser layout."},
        {"id": "AC-02", "text": "Update the server API endpoint and response."},
        {"id": "AC-03", "text": "Persist the database schema change durably."},
    )


def _plan(control: AgenticControlPlane):
    graph = control._work_graph(_multi_domain_acceptance(), source_digest="a" * 64)
    decision = build_team_plan(
        project_id="11111111-1111-4111-8111-111111111111",
        run_id="22222222-2222-4222-8222-222222222222",
        work_specification_id="33333333-3333-4333-8333-333333333333",
        work_specification_revision=1,
        work_specification_digest="b" * 64,
        graph=graph,
        roster=control._roster,
        policy_digest=control._policy_digest,
        limits=control.orchestration_limits,
    )
    assert decision.disposition is OrchestrationDisposition.READY
    assert decision.plan is not None
    return decision.plan


def test_multi_domain_acceptance_builds_one_coherent_implementation_unit():
    control = _control()
    graph = control._work_graph(_multi_domain_acceptance(), source_digest="a" * 64)
    assert graph.approved_acceptance_ids == ("AC-01", "AC-02", "AC-03")
    assert len(graph.units) == 1
    unit = graph.units[0]
    assert unit.unit_id == "implementation"
    assert unit.acceptance_ids == graph.approved_acceptance_ids
    assert unit.coordination_domains == ("source",)
    assert unit.requires_canonical_mutation is False


def test_coherent_implementation_selects_one_initial_agent_but_retains_all_recovery_agents():
    control = _control()
    plan = _plan(control)
    roster_digests = tuple(entry.identity_digest for entry in control._roster.entries)
    assert len(plan.selected_agent_digests) == 1
    assert plan.selected_agent_digests == (roster_digests[0],)
    unit_plan = plan.unit_plan("implementation")
    assert unit_plan.eligible_agent_digests == roster_digests
    assert len(unit_plan.eligible_agent_digests) == 3


def test_coherent_unit_recovery_still_walks_luna_terra_sol_with_existing_ceiling():
    control = _control()
    plan = _plan(control)
    eligible = plan.unit_plan("implementation").eligible_agent_digests
    initial = schedule_team_plan(plan).ready[0]
    assert initial.agent_identity_digest == eligible[0]

    second = candidate_recovery_assignment(
        plan,
        initial,
        attempted_agent_digests=(eligible[0],),
        rejection_count=1,
    )
    assert second is not None
    assert second.agent_identity_digest == eligible[1]

    third = candidate_recovery_assignment(
        plan,
        second,
        attempted_agent_digests=(eligible[0], eligible[1]),
        rejection_count=2,
    )
    assert third is not None
    assert third.agent_identity_digest == eligible[2]

    exhausted = candidate_recovery_assignment(
        plan,
        third,
        attempted_agent_digests=eligible,
        rejection_count=3,
    )
    assert exhausted is None


def test_p2329_does_not_expand_model_timeout_retry_or_final_repair_budgets():
    assert _MODEL_ORDER == (
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-terra",
        "openai/gpt-5.6-sol",
    )
    assert _HOSTED_MODEL_TIMEOUT_SECONDS == 60
    assert _HOSTED_MODEL_NUM_RETRIES == 0
    assert MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT == 1
