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
    WorkGraph,
    WorkUnit,
    build_team_plan,
    schedule_team_plan,
)
from parallax_api.code.optimization_controller import (
    CompetitionCandidate,
    CompetitionContext,
    CompetitionDisposition,
    CompetitionPolicy,
    CompetitionRequest,
    CompletionObservation,
    CompletionState,
    DevelopmentStrategy,
    EconomicMetricPolicy,
    EvidenceState,
    RoutingContext,
    RoutingMetricEvidence,
    RoutingMetricName,
    RoutingPolicy,
    RoutingProvenance,
    RoutingRequest,
    StrategyAdmissionSnapshot,
    StrategyKind,
    StrategyOutcomeEvidence,
    decide_candidate_competition,
    route_outcomes,
)
from parallax_api.code.source_delivery_composition import (
    ProviderActionAuditPair,
    VerifiedDeliveryResult,
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
from parallax_api.evaluation.wave6_agentic_reference import (
    AgenticReferenceCase,
    AgenticReferenceError,
    AutonomousCeiling,
    IntegratedAgenticReferenceProof,
    MeasuredDevelopmentOutcome,
    PreviewEvidence,
    ProtectedExecutionEvidence,
    ReferenceAdmissionReason,
    ReplayRecoveryEvidence,
    TeamClass,
    admit_reference_proof,
    compare_measured_outcomes,
    safe_agentic_reference_json,
)
from parallax_api.tools.contracts import ToolAuditRecord, ToolConsequence, ToolOutcome
from parallax_api.tools.providers import ProviderActionEvidence, ProviderActionState


PROJECT = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
ACCEPTANCE = ("AC-01",)
ORCHESTRATION_POLICY = "b" * 64
CONTENT = "c" * 64


def h(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def agent(name: str) -> AgentIdentity:
    return AgentIdentity(
        agent_id=name,
        agent_version="1.0.0",
        adapter_id=f"{name}-adapter",
        adapter_version="1.0.0",
        provider_kind="reference",
        declared_work_kinds=("implementation", "evaluation"),
        declared_capabilities=("bounded-source-evidence",),
    )


def admitted(identity: AgentIdentity) -> AdmittedAgent:
    return AdmittedAgent(
        identity=identity,
        admitted_work_kinds=("implementation",),
        admitted_capabilities=("bounded-source-evidence",),
    )


def single_plan(producer: AgentIdentity, alternate: AgentIdentity | None = None):
    roster = AdmittedRoster(tuple(admitted(item) for item in ((producer, alternate) if alternate else (producer,))))
    graph = WorkGraph(
        approved_acceptance_ids=ACCEPTANCE,
        units=(
            WorkUnit(
                "implementation",
                "implementation",
                ACCEPTANCE,
                required_capabilities=("bounded-source-evidence",),
                coordination_domains=("application",),
            ),
        ),
    )
    decision = build_team_plan(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        graph=graph,
        roster=roster,
        policy_digest=ORCHESTRATION_POLICY,
    )
    assert decision.disposition is OrchestrationDisposition.READY
    assert decision.plan is not None
    return decision.plan


def supported_evaluation(producer: AgentIdentity, evaluator: AgentIdentity):
    binding = CandidateBinding(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        candidate_lineage_digest=CONTENT,
        candidate_revision_id="revision:reference",
        candidate_attempt_id="attempt:reference",
        producer_identity_digest=producer.digest,
    )
    protected_ref = EvaluationEvidenceReference(
        kind=EvidenceKind.TEST,
        reference_id="test:protected-reference",
        digest=h("protected-test"),
        project_id=PROJECT,
    )
    qualitative_ref = EvaluationEvidenceReference(
        kind=EvidenceKind.DIAGNOSTIC,
        reference_id="diagnostic:independent-reference",
        digest=h("independent-diagnostic"),
        project_id=PROJECT,
    )
    validation = ProtectedValidationEvidence(
        candidate=binding,
        validation_id="validation:reference",
        passed=True,
        acceptance_ids=ACCEPTANCE,
        evidence_refs=(protected_ref,),
    )
    policy = EvaluatorPolicy(
        policy_id="independent-evaluation",
        policy_version="1.0.0",
        acceptance_ids=ACCEPTANCE,
        admitted_evaluator_digests=(evaluator.digest,),
        dimensions=(
            DimensionPolicy(
                dimension="quality",
                required_evidence_kinds=(EvidenceKind.DIAGNOSTIC,),
                allow_score=True,
                minimum_support_score=0.8,
            ),
        ),
    )
    request = EvaluationRequest(
        candidate=binding,
        evaluator=evaluator,
        policy=policy,
        protected_validation=validation,
        qualitative_evidence=(qualitative_ref,),
    )
    judgment = EvaluatorJudgment(
        candidate_digest=binding.digest,
        evaluator_identity_digest=evaluator.digest,
        policy_digest=policy.digest,
        dimensions=(
            DimensionJudgment(
                dimension="quality",
                verdict=DimensionVerdict.SUPPORT,
                finding="independent evidence supports the protected candidate",
                evidence_refs=(qualitative_ref,),
                confidence=0.9,
                score=0.9,
            ),
        ),
    )
    record = evaluate_candidate(request, judgment)
    assert record.outcome is EvaluationOutcome.SUPPORTED
    return binding, validation, policy, record


def routed_candidate(plan, producer, binding, validation, evaluation_policy, evaluation):
    strategy = DevelopmentStrategy(
        strategy_id="reference-strategy",
        strategy_version="1.0.0",
        kind=StrategyKind.SINGLE_AGENT,
        agent_identity_digests=(producer.digest,),
        work_profile="implementation",
        required_capabilities=("bounded-source-evidence",),
        provider_class="reference",
        model_class="bounded-model",
    )
    routing_policy = RoutingPolicy(
        policy_id="outcome-routing",
        policy_version="1.0.0",
        permitted_strategy_kinds=(StrategyKind.SINGLE_AGENT,),
        metric_policies=(
            EconomicMetricPolicy(RoutingMetricName.DURATION, 1.0, 1000.0, required=True),
        ),
        quality_floor=0.8,
        confidence_floor=0.8,
        quality_weight=0.5,
        max_sequence_age=10,
        minimum_comparable_metrics=1,
        human_required_on_insufficient=True,
    )
    routing_context = RoutingContext(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_identity_digest=plan.identity.digest,
        evaluation_policy_digest=evaluation_policy.digest,
        routing_policy_id=routing_policy.policy_id,
        routing_policy_version=routing_policy.policy_version,
        routing_policy_digest=routing_policy.digest,
        decision_id="routing:reference",
        decision_sequence=10,
    )
    admission = StrategyAdmissionSnapshot(
        context_digest=routing_context.digest,
        strategy_digest=strategy.digest,
        project_id=PROJECT,
        source_ref="admission:reference",
        source_digest=h("admission"),
        capability_compatible=True,
        authority_compatible=True,
        dependency_compatible=True,
        admitted_capabilities=("bounded-source-evidence",),
    )
    metric = RoutingMetricEvidence(
        metric=RoutingMetricName.DURATION,
        state=EvidenceState.OBSERVED,
        provenance=RoutingProvenance.PARALLAX,
        source_ref="metric:duration",
        source_digest=h("duration"),
        sequence=10,
        project_id=PROJECT,
        value=120,
        unit="ms",
    )
    outcome = StrategyOutcomeEvidence(
        context_digest=routing_context.digest,
        strategy_digest=strategy.digest,
        project_id=PROJECT,
        protected_validation_passed=True,
        protected_validation_digest=validation.digest,
        evaluation_record=evaluation,
        completion=CompletionObservation(
            state=CompletionState.COMPLETED,
            source_ref="completion:reference",
            source_digest=h("completion"),
            project_id=PROJECT,
        ),
        metrics=(metric,),
    )
    request = RoutingRequest(
        context=routing_context,
        policy=routing_policy,
        strategies=(strategy,),
        admissions=(admission,),
        outcomes=(outcome,),
    )
    routing = route_outcomes(request)
    assert routing.selected_strategy_id == strategy.strategy_id

    competition_policy = CompetitionPolicy(
        policy_id="candidate-competition",
        policy_version="1.0.0",
        max_candidates=4,
        minimum_candidates_for_comparison=2,
        required_candidate_count=1,
        eligibility_quality_floor=0.8,
        winner_quality_floor=0.8,
        winner_confidence_floor=0.8,
        minimum_expected_quality_gain=0.05,
        max_routing_sequence_age=10,
        max_synthesis_attempts=1,
        max_synthesis_parents=2,
        max_rounds=4,
        max_no_progress_rounds=2,
        human_required_on_ambiguity=True,
    )
    competition_context = CompetitionContext(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_identity_digest=plan.identity.digest,
        evaluation_policy_id=evaluation_policy.policy_id,
        evaluation_policy_version=evaluation_policy.policy_version,
        evaluation_policy_digest=evaluation_policy.digest,
        routing_evidence_digest=routing_context.digest,
        competition_policy_id=competition_policy.policy_id,
        competition_policy_version=competition_policy.policy_version,
        competition_policy_digest=competition_policy.digest,
        operation_id="competition:reference",
        operation_sequence=10,
    )
    candidate = CompetitionCandidate(
        candidate_id="reference-candidate",
        binding=binding,
        strategy=strategy,
        producer_identity_digests=(producer.digest,),
        protected_validation=validation,
        evaluation_record=evaluation,
        routing_outcome=outcome,
        assignment_or_team_digest=plan.plan_id,
    )
    competition = decide_candidate_competition(
        CompetitionRequest(
            context=competition_context,
            policy=competition_policy,
            candidates=(candidate,),
        )
    )
    assert competition.disposition is CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT
    assert competition.selected_candidate_id == candidate.candidate_id
    return routing_policy, routing, competition_policy, candidate, competition


def delivery(content_digest=CONTENT, *, replayed=True):
    lineage_id = f"src:{h('lineage')}"
    evidence = ProviderActionEvidence(
        provider="vercel",
        action="preview.create",
        state=ProviderActionState.SUCCEEDED,
        project_ref=PROJECT,
        repository_identity_digest=h("repository"),
        source_revision="reference-revision",
        lineage_id=lineage_id,
        lineage_digest=h("lineage-digest"),
        result_identity="dpl_reference",
        result_status="READY",
        safe_url="https://reference-preview.vercel.app",
    )
    audit = ToolAuditRecord(
        request_id="request:preview-reference",
        capability_id="cap:preview-reference",
        project_ref=PROJECT,
        tool="vercel",
        action="preview.create",
        actor_ref="actor:protected-runtime",
        consequence=ToolConsequence.MUTATE,
        authority_allowed=True,
        outcome=ToolOutcome.SUCCEEDED,
        deny_reason=None,
        approval_id=None,
        request_digest=h("preview-request"),
        result_digest=h("preview-result"),
        result_code="READY",
        result_identity="dpl_reference",
    )
    pair = ProviderActionAuditPair(evidence=evidence, audit=audit)
    return VerifiedDeliveryResult(
        project_id=PROJECT,
        run_id=RUN,
        repository_identity_digest=h("repository"),
        lineage_id=lineage_id,
        content_digest=content_digest,
        branch_name="parallax/reference-proof",
        commit_revision="reference-revision",
        pull_request_number=300,
        pull_request_url="https://github.com/Ryan9876/parallax/pull/300",
        preview_deployment_id="dpl_reference",
        preview_status="READY",
        preview_url="https://reference-preview.vercel.app",
        actions=(pair,),
        replayed=replayed,
    )


def integrated_fixture(*, replay=True, recovery=True, baseline=True):
    producer = agent("producer")
    evaluator = agent("evaluator")
    alternate = agent("alternate")
    plan = single_plan(producer, alternate)
    binding, validation, evaluation_policy, evaluation = supported_evaluation(producer, evaluator)
    routing_policy, routing, competition_policy, candidate, competition = routed_candidate(
        plan, producer, binding, validation, evaluation_policy, evaluation
    )
    case = AgenticReferenceCase(
        case_id="single-agent-reference",
        version="1.0.0",
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_policy_digest=ORCHESTRATION_POLICY,
        evaluation_policy_digest=evaluation_policy.digest,
        routing_policy_digest=routing_policy.digest,
        competition_policy_digest=competition_policy.digest,
        expected_team_class=TeamClass.SINGLE,
        expected_terminal=AutonomousCeiling.REVIEW,
        require_preview=True,
        require_replay=replay,
        require_recovery=recovery,
        baseline_class="wave5-generalized-app" if baseline else None,
    )
    comparison = None
    if baseline:
        comparison = compare_measured_outcomes(
            "wave5-generalized-app",
            MeasuredDevelopmentOutcome(
                evidence_digest=h("wave5"),
                completion_reliability=0.8,
                operator_interventions=3,
                quality=0.85,
                cost=None,
                elapsed_ms=1000,
            ),
            MeasuredDevelopmentOutcome(
                evidence_digest=h("wave6"),
                completion_reliability=0.95,
                operator_interventions=1,
                quality=0.90,
                cost=None,
                elapsed_ms=800,
            ),
        )
    proof = IntegratedAgenticReferenceProof(
        case=case,
        team_plan=plan,
        candidate=candidate,
        evaluation=evaluation,
        routing=routing,
        competition=competition,
        protected_execution=ProtectedExecutionEvidence(
            accepted_content_digest=CONTENT,
            build_digest=h("build"),
            test_digest=h("test"),
            verify_digest=h("verify"),
        ),
        terminal=AutonomousCeiling.REVIEW,
        recovery=ReplayRecoveryEvidence(
            process_recreated=replay,
            recovery_or_reassignment_observed=recovery,
            generation_advanced=recovery,
            accepted_source_mutations=1,
            preview_publications=1,
        ),
        preview=PreviewEvidence.from_delivery(delivery(replayed=replay)),
        baseline_comparison=comparison,
    )
    return proof


def test_permanent_integrated_reference_composes_exact_s1_s5_and_preview_evidence():
    proof = integrated_fixture()
    assert len(proof.team_plan.selected_agent_digests) == 1
    assert proof.evaluation.outcome is EvaluationOutcome.SUPPORTED
    assert proof.routing.selected_strategy_id == proof.candidate.strategy.strategy_id
    assert proof.competition.selected_candidate_id == proof.candidate.candidate_id
    assert proof.preview is not None and proof.preview.replayed
    assert proof.terminal is AutonomousCeiling.REVIEW
    assert proof.baseline_comparison is not None
    assert set(proof.baseline_comparison.improved_dimensions) >= {
        "completion_reliability",
        "operator_interventions",
    }


def test_reference_proof_is_deterministic_duplicate_safe_and_conflict_fail_closed():
    first = integrated_fixture()
    second = integrated_fixture()
    assert first.fingerprint == second.fingerprint
    accepted = admit_reference_proof(first, expected_case=first.case, expected_fingerprint=first.fingerprint)
    assert accepted.admitted and accepted.reason is ReferenceAdmissionReason.ACCEPTED
    duplicate = admit_reference_proof(second, expected_case=first.case, existing=first)
    assert duplicate.duplicate and duplicate.reason is ReferenceAdmissionReason.DUPLICATE
    changed_case = replace(first.case, version="1.0.1")
    rejected = admit_reference_proof(first, expected_case=changed_case)
    assert not rejected.admitted and rejected.reason is ReferenceAdmissionReason.CASE_MISMATCH


def test_exact_delivery_content_mismatch_fails_closed():
    proof = integrated_fixture(replay=False, recovery=False, baseline=False)
    wrong_preview = PreviewEvidence.from_delivery(delivery(content_digest="d" * 64, replayed=False))
    with pytest.raises(AgenticReferenceError, match="exact protected candidate content"):
        replace(proof, preview=wrong_preview)


def test_replay_requires_process_recreation_exactly_once_and_replayed_publication():
    proof = integrated_fixture()
    with pytest.raises(AgenticReferenceError, match="process recreation"):
        replace(proof, recovery=replace(proof.recovery, process_recreated=False))
    assert proof.preview is not None
    with pytest.raises(AgenticReferenceError, match="replay-safe Preview"):
        replace(proof, preview=replace(proof.preview, replayed=False))
    with pytest.raises(AgenticReferenceError):
        replace(proof, recovery=replace(proof.recovery, preview_publications=2))


def test_safe_reference_serialization_contains_only_bounded_evidence_and_no_new_authority():
    proof = integrated_fixture()
    payload = json.loads(safe_agentic_reference_json(proof))
    for key in (
        "contains_source_bytes",
        "contains_prompts",
        "contains_hidden_reasoning",
        "contains_credentials",
        "contains_provider_payload",
        "creates_capability",
        "accepts_source_lineage",
        "performs_merge",
        "performs_production_deployment",
        "completes_review",
        "resolves_human_required",
    ):
        assert payload[key] is False
    rendered = json.dumps(payload).lower()
    assert "api_key" not in rendered
    assert "authorization:" not in rendered
    assert "-----begin" not in rendered


def test_wave5_comparison_keeps_unknown_cost_unknown_and_rejects_no_improvement():
    baseline = MeasuredDevelopmentOutcome(h("base"), 0.8, 2, 0.9, None, 1000)
    challenger = MeasuredDevelopmentOutcome(h("challenger"), 0.9, 1, 0.9, None, 900)
    comparison = compare_measured_outcomes("wave5-generalized-app", baseline, challenger)
    assert "cost" not in comparison.comparable_dimensions
    assert comparison.challenger.cost is None
    with pytest.raises(AgenticReferenceError, match="measured improvement"):
        compare_measured_outcomes(
            "wave5-generalized-app",
            baseline,
            MeasuredDevelopmentOutcome(h("same"), 0.8, 2, 0.9, None, 1000),
        )


def test_multi_agent_parallel_and_overlapping_coordination_fixtures_remain_server_owned():
    first, second = agent("parallel-a"), agent("parallel-b")
    roster = AdmittedRoster((admitted(first), admitted(second)))
    parallel = WorkGraph(
        approved_acceptance_ids=("AC-01", "AC-02"),
        units=(
            WorkUnit("api", "implementation", ("AC-01",), required_capabilities=("bounded-source-evidence",), coordination_domains=("backend",)),
            WorkUnit("ui", "implementation", ("AC-02",), required_capabilities=("bounded-source-evidence",), coordination_domains=("frontend",)),
        ),
    )
    decision = build_team_plan(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        graph=parallel,
        roster=roster,
        policy_digest=ORCHESTRATION_POLICY,
    )
    assert decision.plan is not None and len(decision.plan.selected_agent_digests) == 2
    assert len(schedule_team_plan(decision.plan).ready) == 2

    overlapping = WorkGraph(
        approved_acceptance_ids=("AC-01", "AC-02"),
        units=(
            WorkUnit("api", "implementation", ("AC-01",), required_capabilities=("bounded-source-evidence",), coordination_domains=("shared",)),
            WorkUnit("ui", "implementation", ("AC-02",), required_capabilities=("bounded-source-evidence",), coordination_domains=("shared",)),
        ),
    )
    serial = build_team_plan(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=6,
        work_specification_digest=SPEC_DIGEST,
        graph=overlapping,
        roster=roster,
        policy_digest=ORCHESTRATION_POLICY,
    )
    assert serial.plan is not None and len(serial.plan.selected_agent_digests) == 1
    schedule = schedule_team_plan(serial.plan)
    assert len(schedule.ready) == 1
    assert any(item.disposition is OrchestrationDisposition.SERIALIZED_COORDINATION for item in schedule.assignments)


def test_producer_self_evaluation_stays_blocked_before_integrated_proof():
    producer = agent("self-producer")
    binding, validation, policy, _ = supported_evaluation(producer, agent("independent"))
    self_policy = replace(policy, admitted_evaluator_digests=(producer.digest,))
    request = EvaluationRequest(
        candidate=binding,
        evaluator=producer,
        policy=self_policy,
        protected_validation=validation,
        qualitative_evidence=(),
    )
    ref = validation.evidence_refs[0]
    judgment = EvaluatorJudgment(
        candidate_digest=binding.digest,
        evaluator_identity_digest=producer.digest,
        policy_digest=self_policy.digest,
        dimensions=(
            DimensionJudgment(
                dimension="quality",
                verdict=DimensionVerdict.SUPPORT,
                finding="producer claims its own result is acceptable",
                evidence_refs=(ref,),
                confidence=1.0,
                score=1.0,
            ),
        ),
    )
    record = evaluate_candidate(request, judgment)
    assert record.outcome is EvaluationOutcome.NOT_INDEPENDENT
    assert record.reason_code == "PRODUCER_EVALUATOR_IDENTITY_MATCH"
