from __future__ import annotations

from dataclasses import replace

import pytest

from parallax_api.code.agent_run_projection import (
    AgentRunProjection,
    DeterministicDisposition,
    DeliveryProjection,
    EvaluationProjection,
    ProjectedTask,
    ProjectionIdentity,
    ProjectionKnownState,
    ProjectionMetric,
    ProjectionMetricEvidence,
    RecoveryProjection,
    RoutingProjection,
    ValidationProjection,
)
from parallax_api.code.agentic_observability import (
    AgenticRunObservability,
    QualityProjection,
    RuntimeEvidenceCoverage,
    RuntimeMetricEvidence,
    RuntimeMetricId,
)
from parallax_api.code.domain import AttemptStatus, WorkflowStage
from parallax_api.evaluation.integrated_product_proof import (
    BrowserProofBundle,
    IntegratedProductProofError,
    ProofBrowserState,
    ProofCoverageState,
    ProofDisposition,
    ProofObjectiveClass,
    WAVE7_PROOF_SCENARIOS,
    build_integrated_product_proof,
    build_scenario_proof,
    safe_integrated_product_proof_json,
    safe_scenario_proof_json,
    wave7_proof_portfolio_digest,
)
from parallax_api.evaluation.parallax_bench import (
    BenchmarkCase,
    BenchmarkDimension,
    BenchmarkEvidenceState,
    BenchmarkProvenance,
    CandidateBenchmarkEvidence,
    CandidateBinding,
    DimensionEvidence,
    ParallaxBenchResult,
    ProtectedCeiling,
    ProtectedFloor,
    evaluate_parallax_bench,
)
from parallax_api.tools.browser_evidence import (
    BrowserAction,
    BrowserEvidenceRecord,
    BrowserOutcome,
    BrowserTarget,
)


PROJECT_IDS = {
    "stateful-workflow": "11111111-1111-4111-8111-111111111111",
    "data-operations": "22222222-2222-4222-8222-222222222222",
    "public-utility": "33333333-3333-4333-8333-333333333333",
}
RUN_IDS = {
    "stateful-workflow": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
    "data-operations": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
    "public-utility": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3",
}
WORK_SPEC_IDS = {
    "stateful-workflow": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1",
    "data-operations": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2",
    "public-utility": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb3",
}
WORK_SPEC_DIGESTS = {
    "stateful-workflow": "a" * 64,
    "data-operations": "b" * 64,
    "public-utility": "c" * 64,
}
LINEAGE_DIGESTS = {
    "stateful-workflow": "1" * 64,
    "data-operations": "2" * 64,
    "public-utility": "3" * 64,
}


def _tasks(*, deterministic_passed: bool = True) -> tuple[ProjectedTask, ...]:
    rows = []
    for index, stage in enumerate(
        (
            WorkflowStage.PLAN.value,
            WorkflowStage.IMPLEMENT.value,
            WorkflowStage.BUILD.value,
            WorkflowStage.TEST.value,
            WorkflowStage.VERIFY.value,
        ),
        start=1,
    ):
        status = AttemptStatus.PASSED.value
        failure_code = None
        if not deterministic_passed and stage == WorkflowStage.TEST.value:
            status = AttemptStatus.FAILED.value
            failure_code = "DETERMINISTIC_TEST_FAILURE"
        rows.append(
            ProjectedTask(
                task_id=f"attempt:00000000-0000-4000-8000-00000000000{index}",
                stage=stage,
                attempt_number=1,
                status=status,
                producer_ref="program:protected-runtime",
                failure_code=failure_code,
                started_at=f"2026-08-28T15:0{index}:00+00:00",
                completed_at=f"2026-08-28T15:0{index}:30+00:00",
            )
        )
    return tuple(rows)


def _projection(
    scenario_id: str,
    *,
    deterministic_passed: bool = True,
    recovery: bool | None = None,
    parent_lineage: str | None = None,
) -> AgentRunProjection:
    scenario = WAVE7_PROOF_SCENARIOS[scenario_id]
    project_id = PROJECT_IDS[scenario_id]
    run_id = RUN_IDS[scenario_id]
    lineage = f"src:{LINEAGE_DIGESTS[scenario_id]}"
    if parent_lineage is None and scenario.requires_parent_lineage:
        parent_lineage = f"src:{'0' * 64}"
    use_recovery = scenario.requires_recovery if recovery is None else recovery
    disposition = DeterministicDisposition.PASSED if deterministic_passed else DeterministicDisposition.FAILED
    validations = tuple(
        ValidationProjection(
            stage=stage,
            disposition=(
                DeterministicDisposition.FAILED
                if not deterministic_passed and stage == WorkflowStage.TEST.value
                else DeterministicDisposition.PASSED
            ),
            attempt_id=f"00000000-0000-4000-8000-00000000000{index}",
            failure_code=("DETERMINISTIC_TEST_FAILURE" if not deterministic_passed and stage == WorkflowStage.TEST.value else None),
        )
        for index, stage in enumerate(
            (WorkflowStage.BUILD.value, WorkflowStage.TEST.value, WorkflowStage.VERIFY.value),
            start=3,
        )
    )
    return AgentRunProjection(
        identity=ProjectionIdentity(
            project_id=project_id,
            run_id=run_id,
            work_specification_id=WORK_SPEC_IDS[scenario_id],
            work_specification_revision=1,
            work_specification_digest=WORK_SPEC_DIGESTS[scenario_id],
            acceptance_ids=scenario.required_acceptance_ids,
        ),
        current_state=WorkflowStage.REVIEW.value,
        run_revision=12,
        resume_stage=None,
        last_failure_code=(None if deterministic_passed else "DETERMINISTIC_TEST_FAILURE"),
        latest_source_lineage_ref=lineage,
        tasks=_tasks(deterministic_passed=deterministic_passed),
        recovery=RecoveryProjection(
            execution_id=("cccccccc-cccc-4ccc-8ccc-cccccccccccc" if use_recovery else None),
            state=("RECOVERED" if use_recovery else None),
            lease_generation=(2 if use_recovery else None),
            checkpoint_revision=(3 if use_recovery else None),
            current_step=(WorkflowStage.VERIFY.value if use_recovery else None),
            source_lineage_ref=(lineage if use_recovery else None),
            last_known_good_lineage_ref=(parent_lineage if use_recovery else None),
            retry_count=(1 if use_recovery else None),
            no_progress_count=(0 if use_recovery else None),
            oscillation_count=(0 if use_recovery else None),
            blocker_code=None,
            next_recovery_action=None,
        ),
        validation=validations,
        deterministic_disposition=disposition,
        evaluation=EvaluationProjection(
            evaluation_id="eval-wave7-s6",
            outcome="PASSED",
            score_class="SUPPORTED",
            source_lineage_ref=lineage,
        ),
        routing=RoutingProjection(
            provider="github",
            result_code="SOURCE_ACCEPTED",
            outcome="SUCCEEDED",
            source_lineage_ref=lineage,
        ),
        delivery=DeliveryProjection(
            source_lineage_ref=lineage,
            parent_source_lineage_ref=parent_lineage,
            pull_request_number=400,
            preview_deployment_id=f"dpl-w7-{scenario_id}",
            preview_status="READY",
            artifact_ref=f"preview:{scenario_id}",
        ),
        metrics=(
            ProjectionMetricEvidence(ProjectionMetric.ELAPSED_TIME, ProjectionKnownState.OBSERVED, 900.0, "run:timestamps"),
            ProjectionMetricEvidence(ProjectionMetric.COST_USAGE, ProjectionKnownState.UNKNOWN, None, None),
            ProjectionMetricEvidence(ProjectionMetric.HUMAN_INTERVENTIONS, ProjectionKnownState.OBSERVED, 1.0, "run:events"),
        ),
        advertised_controls=(),
        final_handoff="HUMAN_REQUIRED",
        latest_event_sequence=24,
    )


def _observability(
    projection: AgentRunProjection,
    *,
    complete: bool = True,
    available: bool = True,
    deterministic_passed: bool = True,
) -> AgenticRunObservability:
    disposition = DeterministicDisposition.PASSED if deterministic_passed else DeterministicDisposition.FAILED
    metrics = (
        RuntimeMetricEvidence(RuntimeMetricId.RUN_ELAPSED_SECONDS, ProjectionKnownState.OBSERVED, 900.0, "run:timestamps:v1"),
        RuntimeMetricEvidence(RuntimeMetricId.PROVIDER_COST_USD, ProjectionKnownState.UNKNOWN, None, None),
    )
    return AgenticRunObservability(
        project_id=projection.identity.project_id,
        run_id=projection.identity.run_id,
        run_state=projection.current_state,
        run_revision=projection.run_revision,
        projection_fingerprint=projection.fingerprint,
        latest_event_sequence=projection.latest_event_sequence,
        metrics=metrics,
        s2_compatible_metrics=projection.metrics,
        quality=QualityProjection(
            deterministic_disposition=disposition,
            effective_disposition=disposition,
            evaluation_outcome="PASSED",
            preview_status="READY",
            deterministic_failure_authoritative=not deterministic_passed,
        ),
        coverage=RuntimeEvidenceCoverage(
            attempt_count=len(projection.tasks),
            unique_event_count=projection.latest_event_sequence if available else 0,
            event_plane_available=available,
            event_plane_complete=(complete if available else False),
            worker_evidence_available=projection.recovery.execution_id is not None,
            known_metric_count=1,
            estimated_metric_count=0,
            unknown_metric_count=1,
        ),
    )


def _dimension(
    dimension: BenchmarkDimension,
    value: float | None,
    *,
    state: BenchmarkEvidenceState = BenchmarkEvidenceState.OBSERVED,
    provenance: BenchmarkProvenance = BenchmarkProvenance.PARALLAX_OBSERVED,
    marker: str = "4",
) -> DimensionEvidence:
    return DimensionEvidence(
        dimension=dimension,
        state=state,
        provenance=provenance,
        value=value,
        evidence_ref=f"evidence:{dimension.value}",
        evidence_digest=marker * 64,
    )


def _candidate_evidence(
    scenario_id: str,
    projection: AgentRunProjection,
    *,
    baseline: bool,
    improve_value: bool = True,
    regress_value: bool = False,
    deterministic_passed: bool = True,
) -> CandidateBenchmarkEvidence:
    scenario = WAVE7_PROOF_SCENARIOS[scenario_id]
    lineage_digest = LINEAGE_DIGESTS[scenario_id]
    candidate_id = scenario.baseline_candidate_id if baseline else f"wave7-{scenario_id}"
    binding = CandidateBinding(
        project_id=projection.identity.project_id,
        run_id=(
            "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
            if baseline
            else projection.identity.run_id
        ),
        work_specification_id=projection.identity.work_specification_id,
        work_specification_revision=projection.identity.work_specification_revision,
        work_specification_digest=projection.identity.work_specification_digest,
        acceptance_ids=projection.identity.acceptance_ids,
        candidate_id=candidate_id,
        source_context_digest=("9" * 64 if baseline else lineage_digest),
        protected_validation_digest="d" * 64,
        evaluator_policy_digest="e" * 64,
    )
    protected = ProtectedFloor(
        acceptance_complete=True,
        deterministic_validation_passed=deterministic_passed,
        safety_preserved=True,
        privacy_preserved=True,
        governance_preserved=True,
        review_ceiling_preserved=True,
        human_required=True,
        evidence_digest="f" * 64,
    )

    values = {
        BenchmarkDimension.OBJECTIVE_COMPLETION: 1.0,
        BenchmarkDimension.PROTECTED_CORRECTNESS: (1.0 if deterministic_passed else 0.0),
        BenchmarkDimension.VISUAL_UX_QUALITY: 0.70,
        BenchmarkDimension.HUMAN_INTERVENTIONS: 2.0,
        BenchmarkDimension.ELAPSED_TIME: 1000.0,
        BenchmarkDimension.COST_USAGE: None,
        BenchmarkDimension.RETRY_RECOVERY: 1.0,
        BenchmarkDimension.COMPLETION_RELIABILITY: 0.85,
    }
    if not baseline:
        if scenario.value_dimension is BenchmarkDimension.HUMAN_INTERVENTIONS:
            values[scenario.value_dimension] = 3.0 if regress_value else (1.0 if improve_value else 2.0)
        elif scenario.value_dimension is BenchmarkDimension.COMPLETION_RELIABILITY:
            values[scenario.value_dimension] = 0.75 if regress_value else (0.92 if improve_value else 0.85)
        elif scenario.value_dimension is BenchmarkDimension.VISUAL_UX_QUALITY:
            values[scenario.value_dimension] = 0.60 if regress_value else (0.78 if improve_value else 0.70)

    dimensions = []
    for dimension in BenchmarkDimension:
        value = values[dimension]
        if dimension is BenchmarkDimension.PROTECTED_CORRECTNESS:
            dimensions.append(_dimension(dimension, value, provenance=BenchmarkProvenance.PROTECTED, marker="5"))
        elif dimension is BenchmarkDimension.COST_USAGE:
            dimensions.append(
                _dimension(
                    dimension,
                    None,
                    state=BenchmarkEvidenceState.UNKNOWN,
                    provenance=BenchmarkProvenance.FIXTURE_BOUND,
                    marker="6",
                )
            )
        elif dimension is BenchmarkDimension.VISUAL_UX_QUALITY and not deterministic_passed:
            dimensions.append(
                _dimension(
                    dimension,
                    None,
                    state=BenchmarkEvidenceState.UNKNOWN,
                    provenance=BenchmarkProvenance.FIXTURE_BOUND,
                    marker="7",
                )
            )
        else:
            dimensions.append(_dimension(dimension, value, marker="8" if baseline else "9"))
    return CandidateBenchmarkEvidence(binding=binding, protected_floor=protected, dimensions=tuple(dimensions))


def _benchmark(
    scenario_id: str,
    projection: AgentRunProjection,
    *,
    improve_value: bool = True,
    regress_value: bool = False,
    deterministic_passed: bool = True,
):
    scenario = WAVE7_PROOF_SCENARIOS[scenario_id]
    case = BenchmarkCase(
        case_id=scenario.benchmark_case_id,
        case_version=scenario.scenario_version,
        objective_class=scenario.objective_class.value,
        project_id=projection.identity.project_id,
        work_specification_id=projection.identity.work_specification_id,
        work_specification_revision=projection.identity.work_specification_revision,
        work_specification_digest=projection.identity.work_specification_digest,
        acceptance_ids=projection.identity.acceptance_ids,
        repository_shape=scenario.repository_shape,
        comparable_dimensions=(BenchmarkDimension.PROTECTED_CORRECTNESS, scenario.value_dimension),
        expected_ceiling=ProtectedCeiling.HUMAN_REQUIRED,
        fixture_digest=scenario.fixture_digest,
    )
    baseline = _candidate_evidence(
        scenario_id,
        projection,
        baseline=True,
        deterministic_passed=deterministic_passed,
    )
    challenger = _candidate_evidence(
        scenario_id,
        projection,
        baseline=False,
        improve_value=improve_value,
        regress_value=regress_value,
        deterministic_passed=deterministic_passed,
    )
    result = evaluate_parallax_bench(case=case, baseline=baseline, challenger=challenger)
    return case, baseline, challenger, result


def _browser(projection: AgentRunProjection, *, outcome: BrowserOutcome = BrowserOutcome.SUCCEEDED) -> BrowserProofBundle:
    target = BrowserTarget(
        target_id="preview-main",
        project_id=projection.identity.project_id,
        run_id=projection.identity.run_id,
        url="https://preview.example.test/app",
        source_lineage_ref=projection.delivery.source_lineage_ref,
        preview_deployment_id=projection.delivery.preview_deployment_id,
    )
    record = BrowserEvidenceRecord(
        request_id="assert-main-content",
        project_id=projection.identity.project_id,
        run_id=projection.identity.run_id,
        target_id=target.target_id,
        target_digest=target.digest,
        action=BrowserAction.ASSERT,
        outcome=outcome,
        final_url=target.url,
        observations=("Authorization: Bearer should-never-enter-s6-proof",),
        assertion_passed=(True if outcome is BrowserOutcome.SUCCEEDED else None),
        screenshot_digest=None,
        screenshot_size=None,
        viewport_width=390,
        viewport_height=844,
        reason_code=("ASSERTION_PASSED" if outcome is BrowserOutcome.SUCCEEDED else "POLICY_DENIED"),
    )
    return BrowserProofBundle(target=target, records=(record,))


def _record(
    scenario_id: str,
    *,
    improve_value: bool = True,
    regress_value: bool = False,
    deterministic_passed: bool = True,
    recovery: bool | None = None,
    observability_complete: bool = True,
    observability_available: bool = True,
    browser_outcome: BrowserOutcome = BrowserOutcome.SUCCEEDED,
):
    projection = _projection(
        scenario_id,
        deterministic_passed=deterministic_passed,
        recovery=recovery,
    )
    observability = _observability(
        projection,
        complete=observability_complete,
        available=observability_available,
        deterministic_passed=deterministic_passed,
    )
    case, baseline, challenger, result = _benchmark(
        scenario_id,
        projection,
        improve_value=improve_value,
        regress_value=regress_value,
        deterministic_passed=deterministic_passed,
    )
    return build_scenario_proof(
        scenario_id=scenario_id,
        projection=projection,
        observability=observability,
        benchmark_case=case,
        benchmark_baseline=baseline,
        benchmark_challenger=challenger,
        benchmark_result=result,
        browser=_browser(projection, outcome=browser_outcome),
    )


def test_wave7_portfolio_is_fixed_and_materially_different() -> None:
    assert tuple(WAVE7_PROOF_SCENARIOS) == (
        "stateful-workflow",
        "data-operations",
        "public-utility",
    )
    assert {item.objective_class for item in WAVE7_PROOF_SCENARIOS.values()} == set(ProofObjectiveClass)
    assert len({item.value_dimension for item in WAVE7_PROOF_SCENARIOS.values()}) == 3
    assert len(wave7_proof_portfolio_digest()) == 64


def test_complete_portfolio_release_qualifies_but_stops_human_required() -> None:
    records = tuple(_record(scenario_id) for scenario_id in WAVE7_PROOF_SCENARIOS)
    result = build_integrated_product_proof(records)

    assert result.disposition is ProofDisposition.RELEASE_QUALIFIED
    assert result.release_qualified is True
    assert result.protected_passed is True
    assert result.evidence_complete is True
    assert result.material_value_demonstrated is True
    assert result.autonomous_ceiling == "HUMAN_REQUIRED"
    payload = result.as_dict()
    assert payload["performs_merge"] is False
    assert payload["performs_production_deployment"] is False
    assert payload["approves_release"] is False
    assert payload["completes_review"] is False


def test_each_scenario_preserves_exact_identity_lineage_preview_and_handoff() -> None:
    for scenario_id in WAVE7_PROOF_SCENARIOS:
        record = _record(scenario_id)
        assert record.project_id == PROJECT_IDS[scenario_id]
        assert record.run_id == RUN_IDS[scenario_id]
        assert record.work_specification_id == WORK_SPEC_IDS[scenario_id]
        assert record.acceptance_ids == WAVE7_PROOF_SCENARIOS[scenario_id].required_acceptance_ids
        assert record.source_lineage_ref == f"src:{LINEAGE_DIGESTS[scenario_id]}"
        assert record.preview_deployment_id == f"dpl-w7-{scenario_id}"
        assert record.final_handoff == "HUMAN_REQUIRED"
        assert record.deterministic_disposition == DeterministicDisposition.PASSED.value


def test_s5_partial_coverage_remains_explicit_not_fabricated_complete() -> None:
    record = _record("data-operations", observability_complete=False)
    assert record.observability_coverage is ProofCoverageState.PARTIAL
    assert record.evidence_complete is True


def test_s5_unavailable_event_plane_blocks_integrated_evidence_completion() -> None:
    record = _record("data-operations", observability_available=False)
    assert record.observability_coverage is ProofCoverageState.UNAVAILABLE
    assert record.evidence_complete is False
    result = build_integrated_product_proof(
        (
            _record("stateful-workflow"),
            record,
            _record("public-utility"),
        )
    )
    assert result.disposition is ProofDisposition.INCOMPLETE_EVIDENCE


def test_protected_failure_blocks_release_even_with_other_positive_surfaces() -> None:
    failed = _record("stateful-workflow", deterministic_passed=False)
    assert failed.protected_passed is False
    result = build_integrated_product_proof(
        (
            failed,
            _record("data-operations"),
            _record("public-utility"),
        )
    )
    assert result.disposition is ProofDisposition.PROTECTED_BLOCKED
    assert result.release_qualified is False


def test_value_not_demonstrated_when_no_predeclared_dimension_materially_improves() -> None:
    records = tuple(_record(scenario_id, improve_value=False) for scenario_id in WAVE7_PROOF_SCENARIOS)
    result = build_integrated_product_proof(records)
    assert result.disposition is ProofDisposition.VALUE_NOT_DEMONSTRATED
    assert result.material_value_demonstrated is False


def test_value_regression_blocks_release_qualification_even_when_other_cases_improve() -> None:
    result = build_integrated_product_proof(
        (
            _record("stateful-workflow"),
            _record("data-operations", regress_value=True),
            _record("public-utility"),
        )
    )
    assert result.disposition is ProofDisposition.VALUE_NOT_DEMONSTRATED
    assert result.release_qualified is False


def test_recovery_scenario_requires_bounded_recovery_evidence() -> None:
    record = _record("stateful-workflow", recovery=False)
    assert record.recovery_proven is False
    assert record.evidence_complete is False


def test_browser_policy_denial_cannot_satisfy_product_proof() -> None:
    record = _record("public-utility", browser_outcome=BrowserOutcome.POLICY_DENIED)
    assert record.browser_state is ProofBrowserState.FAILED
    assert record.evidence_complete is False


def test_cross_project_s5_evidence_fails_closed() -> None:
    projection = _projection("data-operations")
    observability = _observability(projection)
    observability = replace(observability, project_id=PROJECT_IDS["public-utility"])
    case, baseline, challenger, result = _benchmark("data-operations", projection)
    with pytest.raises(IntegratedProductProofError, match="observability crosses"):
        build_scenario_proof(
            scenario_id="data-operations",
            projection=projection,
            observability=observability,
            benchmark_case=case,
            benchmark_baseline=baseline,
            benchmark_challenger=challenger,
            benchmark_result=result,
            browser=_browser(projection),
        )


def test_stale_s5_revision_fails_closed() -> None:
    projection = _projection("data-operations")
    observability = replace(_observability(projection), run_revision=projection.run_revision - 1)
    case, baseline, challenger, result = _benchmark("data-operations", projection)
    with pytest.raises(IntegratedProductProofError, match="revision is stale"):
        build_scenario_proof(
            scenario_id="data-operations",
            projection=projection,
            observability=observability,
            benchmark_case=case,
            benchmark_baseline=baseline,
            benchmark_challenger=challenger,
            benchmark_result=result,
            browser=_browser(projection),
        )


def test_browser_target_must_match_exact_project_run_lineage_and_preview() -> None:
    projection = _projection("public-utility")
    observability = _observability(projection)
    case, baseline, challenger, result = _benchmark("public-utility", projection)
    browser = _browser(projection)
    wrong_target = BrowserTarget(
        target_id=browser.target.target_id,
        project_id=projection.identity.project_id,
        run_id=projection.identity.run_id,
        url=browser.target.url,
        source_lineage_ref=f"src:{'4' * 64}",
        preview_deployment_id=projection.delivery.preview_deployment_id,
    )
    wrong_record = replace(browser.records[0], target_digest=wrong_target.digest)
    with pytest.raises(IntegratedProductProofError, match="exact accepted source lineage"):
        build_scenario_proof(
            scenario_id="public-utility",
            projection=projection,
            observability=observability,
            benchmark_case=case,
            benchmark_baseline=baseline,
            benchmark_challenger=challenger,
            benchmark_result=result,
            browser=BrowserProofBundle(target=wrong_target, records=(wrong_record,)),
        )


def test_benchmark_case_and_baseline_are_server_owned_not_runtime_redefinable() -> None:
    projection = _projection("data-operations")
    observability = _observability(projection)
    case, baseline, challenger, result = _benchmark("data-operations", projection)
    wrong_case = replace(case, case_id="caller-invented-case")
    with pytest.raises(IntegratedProductProofError, match="immutable S6 scenario policy"):
        build_scenario_proof(
            scenario_id="data-operations",
            projection=projection,
            observability=observability,
            benchmark_case=wrong_case,
            benchmark_baseline=baseline,
            benchmark_challenger=challenger,
            benchmark_result=result,
            browser=_browser(projection),
        )

    wrong_baseline = replace(baseline, binding=replace(baseline.binding, candidate_id="late-favorable-baseline"))
    with pytest.raises(IntegratedProductProofError, match="predeclared server-owned"):
        build_scenario_proof(
            scenario_id="data-operations",
            projection=projection,
            observability=observability,
            benchmark_case=case,
            benchmark_baseline=wrong_baseline,
            benchmark_challenger=challenger,
            benchmark_result=result,
            browser=_browser(projection),
        )


def test_tampered_benchmark_result_cannot_become_canonical_proof_truth() -> None:
    projection = _projection("public-utility")
    observability = _observability(projection)
    case, baseline, challenger, result = _benchmark("public-utility", projection)
    tampered = ParallaxBenchResult(
        benchmark_version=result.benchmark_version,
        case_digest=result.case_digest,
        baseline_digest=result.baseline_digest,
        challenger_digest=result.challenger_digest,
        comparisons=result.comparisons,
        disposition=result.disposition,
        material_improvement=result.material_improvement,
        reason_code=result.reason_code,
        fingerprint="0" * 64,
    )
    with pytest.raises(IntegratedProductProofError, match="does not match exact canonical"):
        build_scenario_proof(
            scenario_id="public-utility",
            projection=projection,
            observability=observability,
            benchmark_case=case,
            benchmark_baseline=baseline,
            benchmark_challenger=challenger,
            benchmark_result=tampered,
            browser=_browser(projection),
        )


def test_portfolio_cannot_be_cherry_picked_duplicated_or_substituted() -> None:
    with pytest.raises(IntegratedProductProofError, match="all immutable"):
        build_integrated_product_proof((_record("stateful-workflow"), _record("data-operations")))

    with pytest.raises(IntegratedProductProofError, match="cherry-picked"):
        build_integrated_product_proof(
            (
                _record("stateful-workflow"),
                _record("stateful-workflow"),
                _record("public-utility"),
            )
        )


def test_exact_replay_is_deterministic_and_read_only() -> None:
    first_records = tuple(_record(scenario_id) for scenario_id in WAVE7_PROOF_SCENARIOS)
    second_records = tuple(_record(scenario_id) for scenario_id in WAVE7_PROOF_SCENARIOS)
    assert tuple(item.fingerprint for item in first_records) == tuple(item.fingerprint for item in second_records)
    first = build_integrated_product_proof(first_records)
    second = build_integrated_product_proof(second_records)
    assert first.fingerprint == second.fingerprint
    assert first.as_dict()["accepts_source_lineage"] is False
    assert first.as_dict()["grants_provider_authority"] is False


def test_s6_serialization_does_not_leak_browser_observation_or_unsafe_payloads() -> None:
    record = _record("public-utility")
    scenario_json = safe_scenario_proof_json(record)
    aggregate_json = safe_integrated_product_proof_json(
        build_integrated_product_proof(
            (
                _record("stateful-workflow"),
                _record("data-operations"),
                record,
            )
        )
    )
    assert "Bearer should-never-enter-s6-proof" not in scenario_json
    assert "preview.example.test" not in scenario_json
    assert "Bearer should-never-enter-s6-proof" not in aggregate_json
    payload = record.as_dict()
    assert payload["contains_source_bytes"] is False
    assert payload["contains_patch"] is False
    assert payload["contains_credentials"] is False
    assert payload["contains_provider_payload"] is False
    assert payload["contains_prompts"] is False
    assert payload["contains_hidden_reasoning"] is False
    assert payload["contains_sensitive_urls"] is False


def test_unknown_s5_cost_remains_unknown_upstream_and_is_never_zero_filled_by_s6() -> None:
    projection = _projection("data-operations")
    observability = _observability(projection)
    cost = next(item for item in observability.metrics if item.metric is RuntimeMetricId.PROVIDER_COST_USD)
    assert cost.state is ProjectionKnownState.UNKNOWN
    assert cost.value is None
    record = _record("data-operations")
    payload = record.as_dict()
    assert "provider_cost_usd" not in payload
    assert "cost_usage" not in payload


def test_parent_lineage_is_required_only_for_the_existing_repository_scenario() -> None:
    projection = _projection("data-operations", parent_lineage="")
    projection = replace(
        projection,
        delivery=replace(projection.delivery, parent_source_lineage_ref=None),
    )
    observability = _observability(projection)
    case, baseline, challenger, result = _benchmark("data-operations", projection)
    with pytest.raises(IntegratedProductProofError, match="parent source lineage"):
        build_scenario_proof(
            scenario_id="data-operations",
            projection=projection,
            observability=observability,
            benchmark_case=case,
            benchmark_baseline=baseline,
            benchmark_challenger=challenger,
            benchmark_result=result,
            browser=_browser(projection),
        )
