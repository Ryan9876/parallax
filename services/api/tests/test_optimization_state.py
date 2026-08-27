from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.agent_protocol import (
    EvidenceKind,
    MetricAvailability,
    MetricName,
    MetricObservation,
    MetricProvenanceKind,
)
from parallax_api.code.optimization_controller import (
    CompletionObservation,
    CompletionState,
    CriticalPathScheduler,
    DependencyGraph,
    DependencyNode,
    DevelopmentStrategy,
    EconomicMetricPolicy,
    EligibilityReason,
    EngineeringAttemptOptimizationStateStore,
    EvidenceState,
    OptimizationNodeKind,
    OptimizationNodeState,
    OptimizationState,
    OptimizationStateConflict,
    OutcomeRoutingError,
    RoutingAdmissionReason,
    RoutingContext,
    RoutingDisposition,
    RoutingMetricEvidence,
    RoutingMetricName,
    RoutingPolicy,
    RoutingProvenance,
    RoutingRequest,
    StrategyAdmissionSnapshot,
    StrategyKind,
    StrategyOutcomeEvidence,
    admit_routing_record,
    route_outcomes,
    safe_routing_json,
)
from parallax_api.db import Base, make_engine
from parallax_api.evaluation.agent_judgment import (
    CandidateBinding,
    DimensionJudgment,
    DimensionVerdict,
    EvaluationEvidenceReference,
    EvaluationOutcome,
    EvaluationRecord,
)
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


PROJECT = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT = "99999999-9999-4999-8999-999999999999"
RUN = "22222222-2222-4222-8222-222222222222"
SPEC = "33333333-3333-4333-8333-333333333333"
SPEC_DIGEST = "a" * 64
ORCHESTRATION_DIGEST = "b" * 64
EVALUATION_POLICY_DIGEST = "c" * 64
AGENT_A = "d" * 64
AGENT_B = "e" * 64
VALIDATION_DIGEST = "f" * 64
ACCEPTANCE = ("AC-01", "AC-02", "AC-03")


def make_policy(*, fallback=None, human=True, explorations=0, required=True, quality=0.7):
    return RoutingPolicy(
        policy_id="outcome-routing",
        policy_version="1.0.0",
        permitted_strategy_kinds=(StrategyKind.SINGLE_AGENT, StrategyKind.TEAM),
        metric_policies=(
            EconomicMetricPolicy(RoutingMetricName.COST, 0.5, 10.0, required=required),
            EconomicMetricPolicy(RoutingMetricName.DURATION, 0.5, 100.0, allow_estimated=True),
        ),
        quality_floor=quality,
        confidence_floor=0.6,
        quality_weight=0.5,
        max_sequence_age=10,
        minimum_comparable_metrics=1,
        fallback_strategy_id=fallback,
        human_required_on_insufficient=human,
        max_explorations=explorations,
    )


def make_context(policy, *, sequence=10):
    return RoutingContext(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=3,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_identity_digest=ORCHESTRATION_DIGEST,
        evaluation_policy_digest=EVALUATION_POLICY_DIGEST,
        routing_policy_id=policy.policy_id,
        routing_policy_version=policy.policy_version,
        routing_policy_digest=policy.digest,
        decision_id="routing:decision-1",
        decision_sequence=sequence,
    )


def make_strategy(name, agent=AGENT_A, *, fallback=False):
    return DevelopmentStrategy(
        strategy_id=name,
        strategy_version="1.0.0",
        kind=StrategyKind.SINGLE_AGENT,
        agent_identity_digests=(agent,),
        work_profile="implementation",
        required_capabilities=("bounded-source-evidence",),
        provider_class="reference",
        model_class="bounded-model",
        conservative_fallback=fallback,
    )


def make_admission(ctx, strategy, *, capability=True, authority=True, dependency=True):
    return StrategyAdmissionSnapshot(
        context_digest=ctx.digest,
        strategy_digest=strategy.digest,
        project_id=PROJECT,
        source_ref=f"admission:{strategy.strategy_id}",
        source_digest=("1" if strategy.strategy_id == "alpha" else "2") * 64,
        capability_compatible=capability,
        authority_compatible=authority,
        dependency_compatible=dependency,
        admitted_capabilities=("bounded-source-evidence",),
    )


def make_evaluation(strategy, *, result=EvaluationOutcome.SUPPORTED, score=0.9, confidence=0.85, project=PROJECT):
    candidate = CandidateBinding(
        project_id=project,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=3,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        candidate_lineage_digest="3" * 64,
        candidate_revision_id=f"revision:{strategy.strategy_id}",
        candidate_attempt_id=f"attempt:{strategy.strategy_id}",
        producer_identity_digest=strategy.agent_identity_digests[0],
    )
    ref = EvaluationEvidenceReference(
        kind=EvidenceKind.DIAGNOSTIC,
        reference_id=f"diagnostic:{strategy.strategy_id}",
        digest="4" * 64,
        project_id=project,
    )
    dimension = DimensionJudgment(
        dimension="maintainability",
        verdict=DimensionVerdict.SUPPORT if result is EvaluationOutcome.SUPPORTED else DimensionVerdict.CONCERN,
        finding="bounded independent quality evidence",
        evidence_refs=(ref,),
        confidence=confidence,
        score=score,
    )
    return EvaluationRecord(
        candidate=candidate,
        evaluator_identity_digest="5" * 64,
        evaluator_id="independent-evaluator",
        evaluator_version="1.0.0",
        policy_id="independent-evaluation",
        policy_version="1.0.0",
        policy_digest=EVALUATION_POLICY_DIGEST,
        protected_validation_digest=VALIDATION_DIGEST,
        fingerprint="6" * 64,
        outcome=result,
        reason_code="SUPPORTED_BY_POLICY" if result is EvaluationOutcome.SUPPORTED else "POLICY_REJECTED",
        dimensions=(dimension,),
        evidence_refs=(ref,),
    )


def make_metric(name, value, *, sequence=10, project=PROJECT, provenance=RoutingProvenance.PARALLAX):
    return RoutingMetricEvidence(
        metric=name,
        state=EvidenceState.OBSERVED,
        provenance=provenance,
        source_ref=f"metric:{name.value}",
        source_digest=("7" if name is RoutingMetricName.COST else "8") * 64,
        project_id=project,
        sequence=sequence,
        value=value,
        unit="usd" if name is RoutingMetricName.COST else "s",
        currency="USD" if name is RoutingMetricName.COST else None,
    )


def make_unknown(name, *, sequence=10):
    return RoutingMetricEvidence(
        metric=name,
        state=EvidenceState.UNKNOWN,
        provenance=None,
        source_ref=f"metric:{name.value}:unknown",
        source_digest="9" * 64,
        project_id=PROJECT,
        sequence=sequence,
    )


def make_outcome(ctx, strategy, *, cost=5.0, duration=50.0, protected=True,
                 evaluation_result=EvaluationOutcome.SUPPORTED, metrics=None,
                 completion=CompletionState.COMPLETED):
    return StrategyOutcomeEvidence(
        context_digest=ctx.digest,
        strategy_digest=strategy.digest,
        project_id=PROJECT,
        protected_validation_passed=protected,
        protected_validation_digest=VALIDATION_DIGEST,
        evaluation_record=make_evaluation(strategy, result=evaluation_result),
        completion=CompletionObservation(
            state=completion,
            source_ref=f"completion:{strategy.strategy_id}",
            source_digest="0" * 64,
            project_id=PROJECT,
        ),
        metrics=metrics if metrics is not None else (
            make_metric(RoutingMetricName.COST, cost),
            make_metric(RoutingMetricName.DURATION, duration),
        ),
    )


def make_request(ctx, policy, strategies, outcomes, *, admissions=None,
                 explorations_used=0, exploration_strategy_id=None):
    return RoutingRequest(
        context=ctx,
        policy=policy,
        strategies=strategies,
        admissions=admissions if admissions is not None else tuple(make_admission(ctx, s) for s in strategies),
        outcomes=outcomes,
        explorations_used=explorations_used,
        exploration_strategy_id=exploration_strategy_id,
    )


def test_exact_identity_and_replay_are_deterministic():
    policy = make_policy(); ctx = make_context(policy); alpha = make_strategy("alpha")
    req = make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha),))
    assert req.fingerprint == make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha),)).fingerprint
    first = route_outcomes(req); second = route_outcomes(req)
    assert first.disposition is RoutingDisposition.SELECTED
    assert first.selected_strategy_id == "alpha"
    assert first.digest == second.digest


def test_economics_only_compare_admissible_strategies():
    policy = make_policy(); ctx = make_context(policy)
    alpha = make_strategy("alpha", AGENT_A); bravo = make_strategy("bravo", AGENT_B)
    record = route_outcomes(make_request(ctx, policy, (alpha, bravo), (
        make_outcome(ctx, alpha, cost=0.01, duration=1, protected=False),
        make_outcome(ctx, bravo, cost=9, duration=90),
    )))
    assert record.selected_strategy_id == "bravo"
    blocked = next(v for v in record.eligibility if v.strategy_id == "alpha")
    assert EligibilityReason.PROTECTED_VALIDATION_REQUIRED in blocked.reasons
    assert blocked.total_score is None


def test_s3_rejection_and_human_boundary_are_non_tradeable():
    policy = make_policy(); ctx = make_context(policy); alpha = make_strategy("alpha")
    rejected = route_outcomes(make_request(ctx, policy, (alpha,), (
        make_outcome(ctx, alpha, cost=0.01, evaluation_result=EvaluationOutcome.POLICY_REJECTED),
    )))
    assert EligibilityReason.EVALUATION_REJECTED in rejected.eligibility[0].reasons
    human = route_outcomes(make_request(ctx, policy, (alpha,), (
        make_outcome(ctx, alpha, completion=CompletionState.HUMAN_REQUIRED),
    )))
    assert human.disposition is RoutingDisposition.HUMAN_REQUIRED


def test_untrusted_agent_self_report_cannot_become_observed_authority():
    source_digest = "1" * 64
    observed = MetricObservation(
        metric=MetricName.COST,
        availability=MetricAvailability.OBSERVED,
        source="agent-result",
        value=1.25,
        unit="usd",
        currency="USD",
        provenance_kind=MetricProvenanceKind.PROVIDER,
        provenance_ref="provider:usage-1",
    )
    rejected = RoutingMetricEvidence.from_agent_metric(
        observed, project_id=PROJECT, source_digest=source_digest, sequence=10,
        admitted_source_digests=frozenset(),
    )
    assert rejected.state is EvidenceState.INVALID
    admitted = RoutingMetricEvidence.from_agent_metric(
        observed, project_id=PROJECT, source_digest=source_digest, sequence=10,
        admitted_source_digests=frozenset({source_digest}),
    )
    assert admitted.state is EvidenceState.OBSERVED
    assert admitted.provenance is RoutingProvenance.PROVIDER


def test_unknown_is_not_zero_and_required_missing_fails_closed():
    policy = make_policy(required=True); ctx = make_context(policy); alpha = make_strategy("alpha")
    record = route_outcomes(make_request(ctx, policy, (alpha,), (
        make_outcome(ctx, alpha, metrics=(make_unknown(RoutingMetricName.COST),)),
    )))
    item = record.eligibility[0]
    assert EligibilityReason.MISSING_MANDATORY_EVIDENCE in item.reasons
    assert item.components[0].raw_value is None
    assert item.components[0].contribution < 0


def test_stale_cross_project_and_conflicting_evidence_fail_closed():
    policy = make_policy(required=True); ctx = make_context(policy, sequence=50); alpha = make_strategy("alpha")
    stale = make_metric(RoutingMetricName.COST, 1, sequence=1)
    record = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, metrics=(stale,)),)))
    assert EligibilityReason.STALE_MANDATORY_EVIDENCE in record.eligibility[0].reasons
    cross = make_metric(RoutingMetricName.COST, 1, project=OTHER_PROJECT, sequence=50)
    record = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, metrics=(cross,)),)))
    assert EligibilityReason.CROSS_PROJECT_EVIDENCE in record.eligibility[0].reasons
    first = make_metric(RoutingMetricName.COST, 1, sequence=50)
    second = replace(first, source_digest="a" * 64, value=2)
    record = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, metrics=(first, second)),)))
    assert EligibilityReason.CONTRADICTORY_EVIDENCE in record.eligibility[0].reasons


def test_quality_floor_is_non_tradeable():
    policy = make_policy(quality=0.7); ctx = make_context(policy); alpha = make_strategy("alpha")
    low = replace(make_outcome(ctx, alpha, cost=0.01), evaluation_record=make_evaluation(alpha, score=0.4))
    record = route_outcomes(make_request(ctx, policy, (alpha,), (low,)))
    assert EligibilityReason.QUALITY_FLOOR_FAILED in record.eligibility[0].reasons
    assert record.disposition is RoutingDisposition.NO_ADMISSIBLE_STRATEGY


def test_policy_mismatch_is_explicit():
    policy = make_policy(); ctx = make_context(policy); changed = replace(policy, quality_floor=0.8); alpha = make_strategy("alpha")
    record = route_outcomes(make_request(ctx, changed, (alpha,), (make_outcome(ctx, alpha),)))
    assert record.disposition is RoutingDisposition.POLICY_REJECTED
    assert record.selected_strategy_id is None


def test_tie_breaker_is_stable_identity_not_arrival_order():
    policy = make_policy(); ctx = make_context(policy)
    alpha = make_strategy("alpha", AGENT_A); bravo = make_strategy("bravo", AGENT_B)
    ao = make_outcome(ctx, alpha, cost=5, duration=50); bo = make_outcome(ctx, bravo, cost=5, duration=50)
    assert route_outcomes(make_request(ctx, policy, (bravo, alpha), (bo, ao))).selected_strategy_id == "alpha"
    assert route_outcomes(make_request(ctx, policy, (alpha, bravo), (ao, bo))).selected_strategy_id == "alpha"


def test_fallback_and_bounded_exploration_are_explicit_and_admissible_only():
    policy = make_policy(fallback="alpha", human=False, explorations=1, required=False)
    ctx = make_context(policy); alpha = make_strategy("alpha", fallback=True); bravo = make_strategy("bravo", AGENT_B)
    unknowns = (make_unknown(RoutingMetricName.COST), make_unknown(RoutingMetricName.DURATION))
    fallback = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, metrics=unknowns),)))
    assert fallback.disposition is RoutingDisposition.FALLBACK_SELECTED
    explored = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, metrics=unknowns),), exploration_strategy_id="alpha"))
    assert explored.disposition is RoutingDisposition.SELECTED and explored.exploration
    blocked = route_outcomes(make_request(ctx, policy, (alpha, bravo), (
        make_outcome(ctx, alpha, metrics=unknowns),
        make_outcome(ctx, bravo, metrics=unknowns, protected=False),
    ), exploration_strategy_id="bravo"))
    assert blocked.selected_strategy_id == "alpha"
    exhausted = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, metrics=unknowns),), explorations_used=1, exploration_strategy_id="alpha"))
    assert exhausted.disposition is RoutingDisposition.FALLBACK_SELECTED and not exhausted.exploration


def test_server_admission_precedes_scoring():
    policy = make_policy(); ctx = make_context(policy); alpha = make_strategy("alpha")
    for snapshot, reason in (
        (make_admission(ctx, alpha, capability=False), EligibilityReason.CAPABILITY_MISMATCH),
        (make_admission(ctx, alpha, authority=False), EligibilityReason.AUTHORITY_MISMATCH),
        (make_admission(ctx, alpha, dependency=False), EligibilityReason.DEPENDENCY_MISMATCH),
    ):
        record = route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, cost=0.01),), admissions=(snapshot,)))
        assert reason in record.eligibility[0].reasons
        assert record.eligibility[0].total_score is None


def test_s3_candidate_binding_must_match_strategy_and_context():
    policy = make_policy(); ctx = make_context(policy); alpha = make_strategy("alpha", AGENT_A); bravo = make_strategy("bravo", AGENT_B)
    mismatched = replace(make_outcome(ctx, alpha), evaluation_record=make_evaluation(bravo))
    record = route_outcomes(make_request(ctx, policy, (alpha,), (mismatched,)))
    assert EligibilityReason.EVALUATION_IDENTITY_MISMATCH in record.eligibility[0].reasons


def test_fingerprint_drift_and_record_admission_are_replay_safe():
    policy = make_policy(); ctx = make_context(policy); alpha = make_strategy("alpha")
    req = make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, cost=5),))
    changed = make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha, cost=6),))
    assert req.fingerprint != changed.fingerprint
    record = route_outcomes(req)
    accepted = admit_routing_record(record, expected_context=ctx, expected_policy=policy, expected_fingerprint=req.fingerprint)
    assert accepted.admitted and accepted.reason is RoutingAdmissionReason.ACCEPTED
    duplicate = admit_routing_record(record, expected_context=ctx, expected_policy=policy, expected_fingerprint=req.fingerprint, existing=record)
    assert duplicate.duplicate and duplicate.reason is RoutingAdmissionReason.DUPLICATE
    competing = replace(record, reason_code="ALTERNATE_RECORD")
    assert admit_routing_record(competing, expected_context=ctx, expected_policy=policy, expected_fingerprint=req.fingerprint, existing=record).reason is RoutingAdmissionReason.COMPETING_RECORD


def test_safe_serialization_exposes_no_execution_authority_or_secret_surface():
    policy = make_policy(); ctx = make_context(policy); alpha = make_strategy("alpha")
    payload = json.loads(safe_routing_json(route_outcomes(make_request(ctx, policy, (alpha,), (make_outcome(ctx, alpha),)))))
    for key in ("grants_capabilities", "invokes_provider", "routes_spending", "accepts_source_lineage", "transitions_engineering_run", "performs_merge", "performs_deployment", "completes_review", "chooses_candidate_winner"):
        assert payload[key] is False
    rendered = json.dumps(payload).lower()
    assert "api_key" not in rendered and "authorization:" not in rendered
    assert "http://" not in rendered and "https://" not in rendered


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0])
def test_numeric_evidence_rejects_invalid_values(value):
    with pytest.raises(OutcomeRoutingError):
        make_metric(RoutingMetricName.COST, value)


def test_estimate_cannot_masquerade_as_observed_and_team_identity_is_exact():
    with pytest.raises(OutcomeRoutingError):
        RoutingMetricEvidence(RoutingMetricName.COST, EvidenceState.OBSERVED, RoutingProvenance.ESTIMATE, "estimate:cost", "1" * 64, 10, PROJECT, 1, "usd", "USD")
    with pytest.raises(OutcomeRoutingError):
        DevelopmentStrategy("team-a", "1.0.0", StrategyKind.TEAM, (AGENT_A, AGENT_B), "implementation")
    team = DevelopmentStrategy("team-a", "1.0.0", StrategyKind.TEAM, (AGENT_A, AGENT_B), "implementation", team_plan_digest="a" * 64)
    assert team.as_dict()["grants_authority"] is False


def test_malformed_identity_and_duplicate_acceptance_fail_closed():
    policy = make_policy(); ctx = make_context(policy)
    with pytest.raises(OutcomeRoutingError):
        replace(ctx, project_id="not-a-uuid")
    with pytest.raises(OutcomeRoutingError):
        replace(ctx, acceptance_ids=("AC-01", "AC-01"))

# Wave 6 S5 candidate competition and synthesis tests.
from parallax_api.code.optimization_controller import (
    CandidateCompetitionEligibility,
    CompetitionAdmissionReason,
    CompetitionCandidate,
    CompetitionContext,
    CompetitionDisposition,
    CompetitionPolicy,
    CompetitionRequest,
    CompetitionSignal,
    CompetitionTriggerDisposition,
    SynthesisRequest,
    admit_competition_record,
    decide_candidate_competition,
    safe_competition_json,
)
from parallax_api.evaluation.agent_judgment import ProtectedValidationEvidence


COMP_ROUTING_DIGEST = "a" * 64


def make_comp_policy(
    *,
    required_candidates=1,
    winner_quality=0.75,
    max_synthesis=0,
    max_no_progress=2,
    max_cost=10.0,
    max_duration=120.0,
):
    return CompetitionPolicy(
        policy_id="candidate-competition",
        policy_version="1.0.0",
        max_candidates=4,
        minimum_candidates_for_comparison=2,
        required_candidate_count=required_candidates,
        eligibility_quality_floor=0.5,
        winner_quality_floor=winner_quality,
        winner_confidence_floor=0.6,
        minimum_expected_quality_gain=0.05,
        max_extra_cost=max_cost,
        max_extra_duration=max_duration,
        max_routing_sequence_age=10,
        economic_metric_policies=(
            EconomicMetricPolicy(RoutingMetricName.COST, 0.5, 10.0, required=True),
            EconomicMetricPolicy(RoutingMetricName.DURATION, 0.5, 100.0),
        ),
        max_synthesis_attempts=max_synthesis,
        max_synthesis_parents=2,
        max_rounds=4,
        max_no_progress_rounds=max_no_progress,
        synthesis_budget_class="bounded",
        human_required_on_ambiguity=False,
    )


def make_comp_context(policy, *, sequence=10):
    return CompetitionContext(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=3,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        orchestration_identity_digest=ORCHESTRATION_DIGEST,
        evaluation_policy_id="independent-evaluation",
        evaluation_policy_version="1.0.0",
        evaluation_policy_digest=EVALUATION_POLICY_DIGEST,
        routing_evidence_digest=COMP_ROUTING_DIGEST,
        competition_policy_id=policy.policy_id,
        competition_policy_version=policy.policy_version,
        competition_policy_digest=policy.digest,
        operation_id="competition:round-1",
        operation_sequence=sequence,
    )


def make_comp_signal(
    *,
    project=PROJECT,
    routing_digest=COMP_ROUTING_DIGEST,
    sequence=10,
    uncertain=True,
    gain=0.10,
    cost=2.0,
    duration=30.0,
):
    return CompetitionSignal(
        routing_evidence_digest=routing_digest,
        project_id=project,
        sequence=sequence,
        material_quality_uncertainty=uncertain,
        expected_quality_gain=gain,
        estimated_extra_cost=cost,
        estimated_extra_duration=duration,
    )


def make_comp_candidate(
    ctx,
    name,
    agent,
    *,
    lineage,
    score=0.9,
    confidence=0.85,
    validation_passed=True,
    evaluation_outcome=EvaluationOutcome.SUPPORTED,
    evaluator_digest="5" * 64,
    routing_project=PROJECT,
    routing_cost=5.0,
    routing_duration=50.0,
):
    strategy = make_strategy(name, agent)
    binding = CandidateBinding(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_id=SPEC,
        work_specification_revision=3,
        work_specification_digest=SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE,
        candidate_lineage_digest=lineage,
        candidate_revision_id=f"revision:{name}",
        candidate_attempt_id=f"attempt:{name}",
        producer_identity_digest=agent,
    )
    protected_ref = EvaluationEvidenceReference(
        kind=EvidenceKind.TEST,
        reference_id=f"test:protected:{name}",
        digest=("1" if name == "alpha" else "2") * 64,
        project_id=PROJECT,
    )
    validation = ProtectedValidationEvidence(
        candidate=binding,
        validation_id=f"validation:{name}",
        passed=validation_passed,
        acceptance_ids=ACCEPTANCE,
        evidence_refs=(protected_ref,),
        failure_codes=() if validation_passed else ("PROTECTED_TEST_FAILED",),
    )
    eval_ref = EvaluationEvidenceReference(
        kind=EvidenceKind.DIAGNOSTIC,
        reference_id=f"diagnostic:competition:{name}",
        digest=("3" if name == "alpha" else "4") * 64,
        project_id=PROJECT,
    )
    dimension = DimensionJudgment(
        dimension="maintainability",
        verdict=DimensionVerdict.SUPPORT if evaluation_outcome is EvaluationOutcome.SUPPORTED else DimensionVerdict.CONCERN,
        finding="bounded independent competition quality evidence",
        evidence_refs=(eval_ref,),
        confidence=confidence,
        score=score,
    )
    evaluation = EvaluationRecord(
        candidate=binding,
        evaluator_identity_digest=evaluator_digest,
        evaluator_id="independent-evaluator",
        evaluator_version="1.0.0",
        policy_id="independent-evaluation",
        policy_version="1.0.0",
        policy_digest=EVALUATION_POLICY_DIGEST,
        protected_validation_digest=validation.digest,
        fingerprint=("6" if name == "alpha" else "7") * 64,
        outcome=evaluation_outcome,
        reason_code="SUPPORTED_BY_POLICY" if evaluation_outcome is EvaluationOutcome.SUPPORTED else "POLICY_REJECTED",
        dimensions=(dimension,),
        evidence_refs=(eval_ref,),
    )
    routing = StrategyOutcomeEvidence(
        context_digest=COMP_ROUTING_DIGEST,
        strategy_digest=strategy.digest,
        project_id=PROJECT,
        protected_validation_passed=validation_passed,
        protected_validation_digest=validation.digest,
        evaluation_record=evaluation,
        completion=CompletionObservation(
            state=CompletionState.COMPLETED,
            source_ref=f"completion:competition:{name}",
            source_digest="9" * 64,
            project_id=PROJECT,
        ),
        metrics=(
            make_metric(RoutingMetricName.COST, routing_cost, project=routing_project),
            make_metric(RoutingMetricName.DURATION, routing_duration, project=routing_project),
        ),
    )
    return CompetitionCandidate(
        candidate_id=name,
        binding=binding,
        strategy=strategy,
        producer_identity_digests=(agent,),
        protected_validation=validation,
        evaluation_record=evaluation,
        routing_outcome=routing,
    )


def make_comp_request(ctx, policy, candidates, *, signal=None, gaps=(), synthesis_used=0, round_number=1, no_progress=0):
    return CompetitionRequest(
        context=ctx,
        policy=policy,
        candidates=tuple(candidates),
        signal=signal,
        synthesis_gap_refs=tuple(gaps),
        synthesis_attempts_used=synthesis_used,
        competition_round=round_number,
        no_progress_rounds=no_progress,
    )


def test_s5_exact_identity_replay_and_multiple_candidates_alone_do_not_force_competition():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64, score=0.90)
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="b" * 64, score=0.80)
    request = make_comp_request(ctx, policy, (bravo, alpha))
    first = decide_candidate_competition(request)
    second = decide_candidate_competition(make_comp_request(ctx, policy, (alpha, bravo)))
    assert first.trigger is CompetitionTriggerDisposition.SINGLE_CANDIDATE_SUFFICIENT
    assert first.disposition is CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT
    assert first.selected_candidate_id == "alpha"
    assert first.digest == second.digest
    assert request.fingerprint == make_comp_request(ctx, policy, (alpha, bravo)).fingerprint


def test_s5_bounded_signal_can_justify_competition_and_stable_winner_is_order_independent():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64, score=0.88, routing_cost=6)
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="b" * 64, score=0.92, routing_cost=8)
    signal = make_comp_signal()
    first = decide_candidate_competition(make_comp_request(ctx, policy, (alpha, bravo), signal=signal))
    second = decide_candidate_competition(make_comp_request(ctx, policy, (bravo, alpha), signal=signal))
    assert first.trigger is CompetitionTriggerDisposition.COMPETE
    assert first.disposition is CompetitionDisposition.WINNER_SUPPORTED
    assert first.selected_candidate_id == "bravo"
    assert first.digest == second.digest


def test_s5_failed_validation_cannot_be_purchased_by_lower_cost():
    policy = make_comp_policy(required_candidates=2)
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(
        ctx,
        "alpha",
        AGENT_A,
        lineage="a" * 64,
        score=0.99,
        validation_passed=False,
        evaluation_outcome=EvaluationOutcome.POLICY_REJECTED,
        routing_cost=0.01,
        routing_duration=1,
    )
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="b" * 64, score=0.90, routing_cost=9)
    record = decide_candidate_competition(make_comp_request(ctx, policy, (alpha, bravo)))
    blocked = next(item for item in record.eligibility if item.candidate_id == "alpha")
    assert not blocked.eligible
    assert "PROTECTED_VALIDATION_REQUIRED" in {reason.value for reason in blocked.reasons}
    assert record.disposition is CompetitionDisposition.INSUFFICIENT_EVIDENCE
    assert record.selected_candidate_id is None


def test_s5_implementer_self_evaluation_is_never_comparison_authority():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(
        ctx,
        "alpha",
        AGENT_A,
        lineage="a" * 64,
        evaluator_digest=AGENT_A,
    )
    record = decide_candidate_competition(make_comp_request(ctx, policy, (alpha,)))
    item = record.eligibility[0]
    assert not item.eligible
    assert "SELF_EVALUATION" in {reason.value for reason in item.reasons}
    assert record.disposition is CompetitionDisposition.NO_ELIGIBLE_CANDIDATE


def test_s5_same_lineage_cannot_masquerade_as_two_candidates():
    policy = make_comp_policy(required_candidates=2)
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="a" * 64)
    record = decide_candidate_competition(make_comp_request(ctx, policy, (alpha, bravo)))
    assert record.disposition is CompetitionDisposition.POLICY_REJECTED
    assert record.reason_code == "DUPLICATE_LINEAGE_ALTERNATIVE"


def test_s5_cross_project_s4_evidence_is_disqualified_before_scoring():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(
        ctx,
        "alpha",
        AGENT_A,
        lineage="a" * 64,
        routing_project=OTHER_PROJECT,
    )
    record = decide_candidate_competition(make_comp_request(ctx, policy, (alpha,)))
    item = record.eligibility[0]
    assert not item.eligible
    assert "CROSS_PROJECT_EVIDENCE" in {reason.value for reason in item.reasons}


def test_s5_missing_or_stale_signal_never_becomes_free_competition():
    policy = make_comp_policy()
    ctx = make_comp_context(policy, sequence=50)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="b" * 64)
    no_signal = decide_candidate_competition(make_comp_request(ctx, policy, (alpha, bravo)))
    assert no_signal.trigger is CompetitionTriggerDisposition.SINGLE_CANDIDATE_SUFFICIENT
    stale = decide_candidate_competition(
        make_comp_request(ctx, policy, (alpha, bravo), signal=make_comp_signal(sequence=1))
    )
    assert stale.trigger is CompetitionTriggerDisposition.INSUFFICIENT_EVIDENCE
    assert stale.disposition is CompetitionDisposition.INSUFFICIENT_EVIDENCE


def test_s5_signal_budget_bounds_block_extra_competition_without_weakening_quality():
    policy = make_comp_policy(max_cost=1.0, max_duration=10.0)
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="b" * 64)
    record = decide_candidate_competition(
        make_comp_request(ctx, policy, (alpha, bravo), signal=make_comp_signal(cost=2.0, duration=30.0))
    )
    assert record.trigger is CompetitionTriggerDisposition.SINGLE_CANDIDATE_SUFFICIENT
    assert record.selected_candidate_id in {"alpha", "bravo"}


def test_s5_synthesis_is_new_attempt_evidence_and_requires_fresh_validation_and_evaluation():
    policy = make_comp_policy(winner_quality=0.95, max_synthesis=1)
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64, score=0.80)
    bravo = make_comp_candidate(ctx, "bravo", AGENT_B, lineage="b" * 64, score=0.82)
    gap = EvaluationEvidenceReference(
        kind=EvidenceKind.DIAGNOSTIC,
        reference_id="gap:acceptance-quality",
        digest="c" * 64,
        project_id=PROJECT,
    )
    record = decide_candidate_competition(
        make_comp_request(ctx, policy, (alpha, bravo), signal=make_comp_signal(), gaps=(gap,))
    )
    assert record.disposition is CompetitionDisposition.SYNTHESIS_REQUESTED
    synthesis = record.synthesis_request
    assert isinstance(synthesis, SynthesisRequest)
    assert synthesis.fresh_validation_required is True
    assert synthesis.fresh_independent_evaluation_required is True
    assert set(synthesis.parent_lineage_digests) == {"a" * 64, "b" * 64}
    assert synthesis.request_id.startswith("synthesis:")
    assert synthesis.as_dict()["invokes_provider"] is False
    assert synthesis.as_dict()["routes_spending"] is False


def test_s5_parent_validation_cannot_be_reused_for_new_synthesis_lineage():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    parent = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    new_binding = replace(
        parent.binding,
        candidate_lineage_digest="d" * 64,
        candidate_revision_id="revision:synthesized",
        candidate_attempt_id="attempt:synthesized",
    )
    forged = replace(parent, candidate_id="synthesized", binding=new_binding)
    record = decide_candidate_competition(make_comp_request(ctx, policy, (forged,)))
    item = record.eligibility[0]
    assert not item.eligible
    assert "PROTECTED_VALIDATION_MISMATCH" in {reason.value for reason in item.reasons}
    assert "EVALUATION_IDENTITY_MISMATCH" in {reason.value for reason in item.reasons}


def test_s5_bounds_exhaustion_preserves_human_boundary():
    policy = make_comp_policy(max_no_progress=1)
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    record = decide_candidate_competition(make_comp_request(ctx, policy, (alpha,), no_progress=2))
    assert record.trigger is CompetitionTriggerDisposition.HUMAN_REQUIRED
    assert record.disposition is CompetitionDisposition.HUMAN_REQUIRED
    assert record.selected_candidate_id is None


def test_s5_record_admission_is_duplicate_safe_and_conflict_fail_closed():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    request = make_comp_request(ctx, policy, (alpha,))
    record = decide_candidate_competition(request)
    accepted = admit_competition_record(
        record,
        expected_context=ctx,
        expected_policy=policy,
        expected_fingerprint=request.fingerprint,
    )
    assert accepted.admitted and accepted.reason is CompetitionAdmissionReason.ACCEPTED
    duplicate = admit_competition_record(
        record,
        expected_context=ctx,
        expected_policy=policy,
        expected_fingerprint=request.fingerprint,
        existing=record,
    )
    assert duplicate.duplicate and duplicate.reason is CompetitionAdmissionReason.DUPLICATE
    competing = replace(record, reason_code="ALTERNATE_RECORD")
    conflict = admit_competition_record(
        competing,
        expected_context=ctx,
        expected_policy=policy,
        expected_fingerprint=request.fingerprint,
        existing=record,
    )
    assert conflict.reason is CompetitionAdmissionReason.COMPETING_RECORD


def test_s5_safe_serialization_is_evidence_only_and_has_no_execution_surface():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    payload = json.loads(safe_competition_json(decide_candidate_competition(make_comp_request(ctx, policy, (alpha,)))))
    for key in (
        "grants_capabilities",
        "invokes_provider",
        "routes_spending",
        "accepts_source_lineage",
        "transitions_engineering_run",
        "performs_merge",
        "performs_deployment",
        "completes_review",
        "resolves_human_required",
    ):
        assert payload[key] is False
    rendered = json.dumps(payload).lower()
    assert "api_key" not in rendered and "authorization:" not in rendered
    assert "http://" not in rendered and "https://" not in rendered


def test_s5_malformed_policy_and_signal_context_fail_closed():
    policy = make_comp_policy()
    ctx = make_comp_context(policy)
    alpha = make_comp_candidate(ctx, "alpha", AGENT_A, lineage="a" * 64)
    changed = replace(policy, winner_quality_floor=0.99)
    mismatch = decide_candidate_competition(make_comp_request(ctx, changed, (alpha,)))
    assert mismatch.disposition is CompetitionDisposition.POLICY_REJECTED
    wrong_signal = make_comp_signal(project=OTHER_PROJECT)
    signal_record = decide_candidate_competition(make_comp_request(ctx, policy, (alpha,), signal=wrong_signal))
    assert signal_record.disposition is CompetitionDisposition.POLICY_REJECTED
