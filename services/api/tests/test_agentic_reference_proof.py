from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json

import pytest

from parallax_api.code.agent_protocol import AgentIdentity, EvidenceKind
from parallax_api.code.agent_team_orchestration import (
    AdmittedAgent,
    AdmittedRoster,
    OrchestrationDisposition,
    OrchestrationLimits,
    WorkGraph,
    WorkUnit,
    build_team_plan,
    create_agent_task_request,
    reassign_assignment,
    schedule_team_plan,
)
from parallax_api.code.optimization_controller import (
    CandidateCompetitionEligibility,
    CompetitionContext,
    CompetitionDecisionRecord,
    CompetitionDisposition,
    CompetitionEligibilityReason,
    CompetitionTriggerDisposition,
    EligibilityReason,
    RoutingContext,
    RoutingDecisionRecord,
    RoutingDisposition,
    StrategyEligibility,
)
from parallax_api.code.source_delivery_composition import ProviderActionAuditPair, VerifiedDeliveryResult
from parallax_api.code.worker_recovery import (
    RecoveryAction,
    StallClassification,
    WorkerHealthSnapshot,
    WorkerLifecycleState,
)
from parallax_api.evaluation.agent_judgment import (
    CandidateBinding,
    DimensionJudgment,
    DimensionPolicy,
    DimensionVerdict,
    EvaluationEvidenceReference,
    EvaluationOutcome,
    EvaluationRequest,
    EvaluatorJudgment,
    EvaluatorPolicy,
    ProtectedValidationEvidence,
    evaluate_candidate,
)
from parallax_api.evaluation.agentic_reference_proof import (
    AgenticReferenceProofError,
    BenchmarkMetric,
    BenchmarkObservation,
    BenchmarkPair,
    BenchmarkState,
    ReferenceCeiling,
    ReferenceDisposition,
    ReferenceIdentity,
    Wave5Comparison,
    build_agentic_reference_proof,
    safe_reference_proof_json,
)
from parallax_api.tools.contracts import ToolAuditRecord, ToolConsequence, ToolOutcome
from parallax_api.tools.providers import ProviderActionEvidence, ProviderActionState


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
ORCHESTRATION_POLICY = "b" * 64
ROUTING_POLICY = "c" * 64
COMPETITION_POLICY = "d" * 64
LINEAGE = "e" * 64
CONTENT_DIGEST = "f" * 64
REPOSITORY_DIGEST = "1" * 64
ACCEPTANCE = ("AC-01", "AC-02")


def _agent(name: str, *, work_kind: str = "implementation") -> AgentIdentity:
    return AgentIdentity(
        agent_id=name,
        agent_version="1.0.0",
        adapter_id=f"{name}-adapter",
        adapter_version="1.0.0",
        provider_kind="reference",
        declared_work_kinds=(work_kind,),
        declared_capabilities=("source-evidence",) if work_kind == "implementation" else ("evaluation-evidence",),
    )


def _roster() -> AdmittedRoster:
    agents = (_agent("agent-a"), _agent("agent-b"))
    return AdmittedRoster(
        tuple(
            AdmittedAgent(
                identity=item,
                admitted_work_kinds=("implementation",),
                admitted_capabilities=("source-evidence",),
            )
            for item in agents
        )
    )


def _graph(*, serial: bool = False, overlap: bool = False) -> WorkGraph:
    return WorkGraph(
        approved_acceptance_ids=ACCEPTANCE,
        units=(
            WorkUnit(
                unit_id="api",
                work_kind="implementation",
                acceptance_ids=("AC-01",),
                required_capabilities=("source-evidence",),
                coordination_domains=("shared",) if overlap else ("backend",),
            ),
            WorkUnit(
                unit_id="ui",
                work_kind="implementation",
                acceptance_ids=("AC-02",),
                dependencies=("api",) if serial else (),
                required_capabilities=("source-evidence",),
                coordination_domains=("shared",) if overlap else ("frontend",),
            ),
        ),
    )


def _plan(*, serial: bool = False, overlap: bool = False, limits: OrchestrationLimits | None = None):
    decision = build_team_plan(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        graph=_graph(serial=serial, overlap=overlap),
        roster=_roster(),
        policy_digest=ORCHESTRATION_POLICY,
        limits=limits,
    )
    assert decision.disposition is OrchestrationDisposition.READY
    assert decision.plan is not None
    return decision.plan


def _identity() -> ReferenceIdentity:
    return ReferenceIdentity(
        case_id="integrated-reference",
        case_version="1.0.0",
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
    )


def _evaluation(plan, *, validation_passed: bool = True, self_evaluate: bool = False):
    producer_digest = plan.selected_agent_digests[0]
    candidate = CandidateBinding(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        candidate_lineage_digest=LINEAGE,
        candidate_revision_id="revision:candidate-a",
        candidate_attempt_id="attempt:candidate-a",
        producer_identity_digest=producer_digest,
    )
    protected_ref = EvaluationEvidenceReference(
        kind=EvidenceKind.TEST,
        reference_id="test:build-test-verify",
        digest="2" * 64,
        project_id=PROJECT,
    )
    qualitative_ref = EvaluationEvidenceReference(
        kind=EvidenceKind.OBSERVATION,
        reference_id="observation:quality",
        digest="3" * 64,
        project_id=PROJECT,
    )
    protected = ProtectedValidationEvidence(
        candidate=candidate,
        validation_id="validation:protected",
        passed=validation_passed,
        acceptance_ids=ACCEPTANCE,
        evidence_refs=(protected_ref,),
        failure_codes=() if validation_passed else ("PROTECTED_TEST_FAILED",),
    )
    if self_evaluate:
        evaluator = next(
            entry.identity for entry in plan.roster.entries if entry.identity_digest == producer_digest
        )
    else:
        evaluator = _agent("independent-evaluator", work_kind="evaluation")
    policy = EvaluatorPolicy(
        policy_id="independent-evaluation",
        policy_version="1.0.0",
        acceptance_ids=ACCEPTANCE,
        admitted_evaluator_digests=(evaluator.digest,),
        dimensions=(
            DimensionPolicy(
                dimension="quality",
                required_evidence_kinds=(EvidenceKind.OBSERVATION,),
                allow_score=True,
                minimum_support_score=0.70,
            ),
        ),
    )
    request = EvaluationRequest(
        candidate=candidate,
        evaluator=evaluator,
        policy=policy,
        protected_validation=protected,
        qualitative_evidence=(qualitative_ref,),
    )
    judgment = EvaluatorJudgment(
        candidate_digest=candidate.digest,
        evaluator_identity_digest=evaluator.digest,
        policy_digest=policy.digest,
        dimensions=(
            DimensionJudgment(
                dimension="quality",
                verdict=DimensionVerdict.SUPPORT,
                finding="bounded evidence supports the exact candidate",
                evidence_refs=(qualitative_ref,),
                confidence=0.90,
                score=0.90,
            ),
        ),
        claimed_outcome=EvaluationOutcome.SUPPORTED,
    )
    return evaluate_candidate(request, judgment)


def _routing(plan, evaluation) -> RoutingDecisionRecord:
    context = RoutingContext(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_identity_digest=plan.identity.digest,
        evaluation_policy_digest=evaluation.policy_digest,
        routing_policy_id="routing-policy",
        routing_policy_version="1.0.0",
        routing_policy_digest=ROUTING_POLICY,
        decision_id="routing:integrated-reference",
        decision_sequence=1,
    )
    eligibility = StrategyEligibility(
        strategy_id="team-primary",
        strategy_digest="4" * 64,
        eligible=True,
        reasons=(EligibilityReason.ELIGIBLE,),
        quality_score=0.90,
        quality_confidence=0.90,
        comparable_metrics=2,
        components=(),
        total_score=0.90,
    )
    return RoutingDecisionRecord(
        context=context,
        policy_id=context.routing_policy_id,
        policy_version=context.routing_policy_version,
        policy_digest=context.routing_policy_digest,
        fingerprint="5" * 64,
        disposition=RoutingDisposition.SELECTED,
        reason_code="BEST_ADMISSIBLE_STRATEGY",
        selected_strategy_id="team-primary",
        exploration=False,
        eligibility=(eligibility,),
    )


def _competition(plan, evaluation, routing) -> CompetitionDecisionRecord:
    context = CompetitionContext(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=2,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_identity_digest=plan.identity.digest,
        evaluation_policy_id=evaluation.policy_id,
        evaluation_policy_version=evaluation.policy_version,
        evaluation_policy_digest=evaluation.policy_digest,
        routing_evidence_digest=routing.digest,
        competition_policy_id="competition-policy",
        competition_policy_version="1.0.0",
        competition_policy_digest=COMPETITION_POLICY,
        operation_id="competition:integrated-reference",
        operation_sequence=1,
    )
    eligibility = CandidateCompetitionEligibility(
        candidate_id="candidate-a",
        candidate_digest=evaluation.candidate.digest,
        candidate_lineage_digest=LINEAGE,
        eligible=True,
        reasons=(CompetitionEligibilityReason.ELIGIBLE,),
        quality_score=0.90,
        quality_confidence=0.90,
        economic_score=0.80,
    )
    return CompetitionDecisionRecord(
        context=context,
        policy_id=context.competition_policy_id,
        policy_version=context.competition_policy_version,
        policy_digest=context.competition_policy_digest,
        fingerprint="6" * 64,
        trigger=CompetitionTriggerDisposition.SINGLE_CANDIDATE_SUFFICIENT,
        disposition=CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT,
        reason_code="SINGLE_CANDIDATE_SUFFICIENT",
        selected_candidate_id="candidate-a",
        eligibility=(eligibility,),
    )


def _delivery(*, lineage: str = LINEAGE, status: str = "READY", replayed: bool = False) -> VerifiedDeliveryResult:
    evidence = ProviderActionEvidence(
        provider="vercel",
        action="preview.read",
        state=ProviderActionState.SUCCEEDED,
        project_ref=PROJECT,
        repository_identity_digest=REPOSITORY_DIGEST,
        source_revision="commit-s6",
        lineage_id=f"src:{lineage}",
        lineage_digest=CONTENT_DIGEST,
        result_identity="dpl_s6_reference",
        result_status=status,
        safe_url="https://s6-reference.vercel.app",
    )
    request_id = "request:s6-preview-read"
    audit = ToolAuditRecord(
        request_id=request_id,
        capability_id="cap:s6-preview-read",
        project_ref=PROJECT,
        tool="vercel",
        action="preview.read",
        actor_ref="actor:s6-reference",
        consequence=ToolConsequence.READ,
        authority_allowed=True,
        outcome=ToolOutcome.SUCCEEDED,
        deny_reason=None,
        approval_id=None,
        request_digest=sha256(f"{request_id}|vercel|preview.read".encode()).hexdigest(),
        result_digest=sha256(f"{status}|dpl_s6_reference".encode()).hexdigest(),
        result_code=status,
        result_identity="dpl_s6_reference",
    )
    pair = ProviderActionAuditPair(evidence=evidence, audit=audit)
    return VerifiedDeliveryResult(
        project_id=PROJECT,
        run_id=RUN,
        repository_identity_digest=REPOSITORY_DIGEST,
        lineage_id=f"src:{lineage}",
        content_digest=CONTENT_DIGEST,
        branch_name="parallax/run/s6-reference",
        commit_revision="commit-s6",
        pull_request_number=301,
        pull_request_url="https://example.invalid/pr/301",
        preview_deployment_id="dpl_s6_reference",
        preview_status=status,
        preview_url="https://s6-reference.vercel.app",
        actions=(pair,),
        replayed=replayed,
    )


def _observation(metric: BenchmarkMetric, value: float | None, *, baseline: bool, state=BenchmarkState.OBSERVED):
    return BenchmarkObservation(
        metric=metric,
        state=state,
        value=value,
        provenance_ref=f"fixture:{'wave5' if baseline else 'wave6'}:{metric.value}",
        provenance_digest=sha256(
            f"{'wave5' if baseline else 'wave6'}|{metric.value}|{state.value}|{value}".encode()
        ).hexdigest(),
    )


def _benchmark(*, improved: bool = True, guardrails: bool = True) -> Wave5Comparison:
    pairs = (
        BenchmarkPair(
            _observation(BenchmarkMetric.COMPLETION_RELIABILITY, 0.80, baseline=True),
            _observation(BenchmarkMetric.COMPLETION_RELIABILITY, 0.90 if improved else 0.80, baseline=False),
        ),
        BenchmarkPair(
            _observation(BenchmarkMetric.OPERATOR_INTERVENTIONS, 3, baseline=True),
            _observation(BenchmarkMetric.OPERATOR_INTERVENTIONS, 2 if improved else 3, baseline=False),
        ),
        BenchmarkPair(
            _observation(BenchmarkMetric.QUALITY, 0.76, baseline=True),
            _observation(BenchmarkMetric.QUALITY, 0.83 if improved else 0.76, baseline=False),
        ),
        BenchmarkPair(
            _observation(BenchmarkMetric.ELAPSED_TIME, None, baseline=True, state=BenchmarkState.UNKNOWN),
            _observation(BenchmarkMetric.ELAPSED_TIME, None, baseline=False, state=BenchmarkState.UNKNOWN),
        ),
        BenchmarkPair(
            _observation(BenchmarkMetric.COST, None, baseline=True, state=BenchmarkState.INCOMPARABLE),
            _observation(BenchmarkMetric.COST, None, baseline=False, state=BenchmarkState.INCOMPARABLE),
        ),
        BenchmarkPair(
            _observation(BenchmarkMetric.RETRIES, 2, baseline=True),
            _observation(BenchmarkMetric.RETRIES, 1 if improved else 2, baseline=False),
        ),
    )
    return Wave5Comparison(
        pairs=pairs,
        correctness_parity=guardrails,
        safety_parity=guardrails,
        privacy_parity=guardrails,
        governance_parity=guardrails,
    )


def _positive_inputs():
    plan = _plan()
    schedule = schedule_team_plan(plan)
    tasks = tuple(create_agent_task_request(plan, assignment) for assignment in schedule.ready)
    evaluation = _evaluation(plan)
    routing = _routing(plan, evaluation)
    competition = _competition(plan, evaluation, routing)
    return {
        "identity": _identity(),
        "s1_evidence_digests": tuple(task.binding.digest for task in tasks),
        "team_plan": plan,
        "schedule": schedule,
        "evaluation": evaluation,
        "routing": routing,
        "competition": competition,
        "delivery": _delivery(),
        "benchmark": _benchmark(),
    }


def test_s2_smallest_adequate_team_and_coordination_are_exercised_by_reference_suite():
    assert len(_plan(serial=True).selected_agent_digests) == 1
    parallel = _plan()
    assert len(parallel.selected_agent_digests) == 2
    assert len(schedule_team_plan(parallel).ready) == 2
    overlap = _plan(overlap=True)
    assert len(overlap.selected_agent_digests) == 1


def test_reference_recovery_uses_durable_worker_generation_and_is_bounded():
    limits = OrchestrationLimits(
        max_team_size=2,
        max_concurrency=2,
        max_reassignments_per_work_unit=1,
        max_replans=2,
        max_no_progress=2,
    )
    plan = _plan(serial=True, limits=limits)
    current = schedule_team_plan(plan).ready[0]
    health = WorkerHealthSnapshot(
        execution_id="worker:s6",
        project_id=PROJECT,
        run_id=RUN,
        state=WorkerLifecycleState.STALLED,
        lease_status="ACTIVE",
        lease_generation=4,
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
        next_recovery_action=RecoveryAction.REASSIGN,
        human_required=False,
    )
    recovered = reassign_assignment(
        plan,
        current,
        worker_health=health,
        expected_worker_execution_id="worker:s6",
        expected_worker_lease_generation=4,
        reassignment_count=0,
    )
    assert recovered.disposition is OrchestrationDisposition.REASSIGNED
    assert recovered.assignment is not None
    assert recovered.assignment.generation == current.generation + 1

    stale = reassign_assignment(
        plan,
        current,
        worker_health=replace(health, lease_generation=5),
        expected_worker_execution_id="worker:s6",
        expected_worker_lease_generation=4,
        reassignment_count=0,
    )
    assert stale.reason_code == "STALE_WORKER_GENERATION"

    exhausted = reassign_assignment(
        plan,
        current,
        worker_health=health,
        expected_worker_execution_id="worker:s6",
        expected_worker_lease_generation=4,
        reassignment_count=1,
    )
    assert exhausted.disposition is OrchestrationDisposition.HUMAN_REQUIRED

    schedule = schedule_team_plan(plan)
    task = create_agent_task_request(plan, schedule.ready[0])
    evaluation = _evaluation(plan)
    routing = _routing(plan, evaluation)
    competition = _competition(plan, evaluation, routing)
    proof = build_agentic_reference_proof(
        identity=_identity(),
        s1_evidence_digests=(task.binding.digest,),
        team_plan=plan,
        schedule=schedule,
        evaluation=evaluation,
        routing=routing,
        competition=competition,
        delivery=_delivery(),
        benchmark=_benchmark(),
        recoveries=(recovered,),
    )
    assert proof.disposition is ReferenceDisposition.SUPPORTED
    assert proof.recovery_evidence_digests
    assert proof.recovery_summary[0][0] == OrchestrationDisposition.REASSIGNED.value


def test_integrated_reference_proof_is_supported_replay_safe_and_review_bounded():
    inputs = _positive_inputs()
    first = build_agentic_reference_proof(**inputs)
    second = build_agentic_reference_proof(**inputs)
    assert first.disposition is ReferenceDisposition.SUPPORTED
    assert first.reason_code == "INTEGRATED_REFERENCE_PROOF_SUPPORTED"
    assert first.final_ceiling is ReferenceCeiling.REVIEW
    assert first.fingerprint == second.fingerprint
    assert first.result_digest == second.result_digest
    assert first.preview_deployment_id == "dpl_s6_reference"
    assert first.competition_disposition == CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT.value
    assert first.benchmark is not None and first.benchmark.material_improvement


def test_process_recreated_delivery_replay_keeps_same_proof_fingerprint():
    inputs = _positive_inputs()
    original = build_agentic_reference_proof(**inputs)
    replayed_delivery = _delivery(replayed=True)
    replay = build_agentic_reference_proof(**{**inputs, "delivery": replayed_delivery})
    assert replay.disposition is ReferenceDisposition.SUPPORTED
    assert replay.delivery_digest == original.delivery_digest
    assert replay.fingerprint == original.fingerprint
    assert replay.candidate_lineage_digest == original.candidate_lineage_digest
    assert replay.preview_deployment_id == original.preview_deployment_id


def test_exact_identity_or_selected_lineage_substitution_fails_closed():
    inputs = _positive_inputs()
    with pytest.raises(AgenticReferenceProofError, match="S2 plan identity"):
        build_agentic_reference_proof(
            **{
                **inputs,
                "identity": replace(_identity(), project_id=OTHER_PROJECT),
            }
        )
    with pytest.raises(AgenticReferenceProofError, match="Preview delivery lineage"):
        build_agentic_reference_proof(
            **{
                **inputs,
                "delivery": _delivery(lineage="9" * 64),
            }
        )


def test_stale_s4_binding_inside_s5_fails_closed():
    inputs = _positive_inputs()
    competition = inputs["competition"]
    drifted_context = replace(competition.context, routing_evidence_digest="9" * 64)
    drifted = replace(competition, context=drifted_context)
    with pytest.raises(AgenticReferenceProofError, match="exact S4 routing evidence"):
        build_agentic_reference_proof(**{**inputs, "competition": drifted})


def test_deterministic_failure_precedes_routing_competition_cost_or_benchmark_claims():
    plan = _plan()
    schedule = schedule_team_plan(plan)
    tasks = tuple(create_agent_task_request(plan, assignment) for assignment in schedule.ready)
    evaluation = _evaluation(plan, validation_passed=False)
    routing = _routing(plan, evaluation)
    competition = _competition(plan, evaluation, routing)
    result = build_agentic_reference_proof(
        identity=_identity(),
        s1_evidence_digests=tuple(task.binding.digest for task in tasks),
        team_plan=plan,
        schedule=schedule,
        evaluation=evaluation,
        routing=routing,
        competition=competition,
        delivery=_delivery(),
        benchmark=_benchmark(),
    )
    assert evaluation.outcome is EvaluationOutcome.DETERMINISTIC_BLOCKED
    assert result.disposition is ReferenceDisposition.DETERMINISTIC_BLOCKED
    assert result.reason_code == "S3_DETERMINISTIC_BLOCKED"


def test_producer_self_evaluation_cannot_satisfy_independent_quality_proof():
    plan = _plan()
    schedule = schedule_team_plan(plan)
    tasks = tuple(create_agent_task_request(plan, assignment) for assignment in schedule.ready)
    evaluation = _evaluation(plan, self_evaluate=True)
    routing = _routing(plan, evaluation)
    competition = _competition(plan, evaluation, routing)
    result = build_agentic_reference_proof(
        identity=_identity(),
        s1_evidence_digests=tuple(task.binding.digest for task in tasks),
        team_plan=plan,
        schedule=schedule,
        evaluation=evaluation,
        routing=routing,
        competition=competition,
        delivery=_delivery(),
        benchmark=_benchmark(),
    )
    assert evaluation.outcome is EvaluationOutcome.NOT_INDEPENDENT
    assert result.disposition is ReferenceDisposition.POLICY_REJECTED


def test_human_required_ceiling_is_preserved_and_never_resolved_by_proof():
    result = build_agentic_reference_proof(**_positive_inputs(), final_ceiling=ReferenceCeiling.HUMAN_REQUIRED)
    assert result.disposition is ReferenceDisposition.HUMAN_REQUIRED
    assert result.reason_code == "PROTECTED_HUMAN_BOUNDARY"
    payload = result.as_dict()
    assert payload["completes_review"] is False
    assert payload["resolves_human_required"] is False
    assert payload["performs_production_deployment"] is False


def test_wave5_comparison_requires_guardrail_parity_and_material_improvement():
    no_improvement = build_agentic_reference_proof(
        **{**_positive_inputs(), "benchmark": _benchmark(improved=False)}
    )
    assert no_improvement.disposition is ReferenceDisposition.INSUFFICIENT_EVIDENCE
    assert no_improvement.reason_code == "MATERIAL_IMPROVEMENT_NOT_PROVEN"

    regression = build_agentic_reference_proof(
        **{**_positive_inputs(), "benchmark": _benchmark(guardrails=False)}
    )
    assert regression.disposition is ReferenceDisposition.POLICY_REJECTED
    assert regression.reason_code == "BENCHMARK_GUARDRAIL_REGRESSION"


def test_unknown_and_incomparable_benchmark_dimensions_remain_explicit():
    result = build_agentic_reference_proof(**_positive_inputs())
    assert result.benchmark is not None
    by_metric = {pair.metric: pair for pair in result.benchmark.pairs}
    assert by_metric[BenchmarkMetric.ELAPSED_TIME].baseline.state is BenchmarkState.UNKNOWN
    assert by_metric[BenchmarkMetric.COST].challenger.state is BenchmarkState.INCOMPARABLE
    assert not by_metric[BenchmarkMetric.ELAPSED_TIME].comparable
    assert not by_metric[BenchmarkMetric.COST].materially_improved


def test_safe_serialization_exposes_evidence_without_urls_credentials_or_authority():
    result = build_agentic_reference_proof(**_positive_inputs())
    serialized = safe_reference_proof_json(result)
    payload = json.loads(serialized)
    assert payload["disposition"] == "SUPPORTED"
    assert payload["benchmark"]["material_improvement"] is True
    assert payload["grants_capabilities"] is False
    assert payload["accepts_source_lineage"] is False
    assert payload["performs_merge"] is False
    assert payload["performs_production_deployment"] is False
    assert payload["approves_release"] is False
    assert payload["completes_review"] is False
    lowered = serialized.lower()
    for token in (
        "https://",
        "http://",
        "authorization:",
        "bearer ",
        "password=",
        "api_key",
        "raw_provider_payload",
        "rm -rf",
    ):
        assert token not in lowered
