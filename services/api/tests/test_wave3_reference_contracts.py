from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from parallax_api.code.autonomous_correction import (
    AutonomousCorrectionController,
    CandidateValidation,
    CorrectionBudgetPolicy,
    CorrectionContext,
    CorrectionMutationResult,
    CorrectionPlan,
    CorrectionSessionState,
    CorrectionSessionStatus,
    CorrectionStateConflict,
    DefectSource,
    ProtectedQualityVector,
    candidate_from_browser,
)
from parallax_api.code.optimization_controller import (
    ChangeImpactGraph,
    DevelopmentPhase,
    ImpactRule,
    OptimizationPolicyError,
    PhaseObservation,
    RepairMemory,
    RepairMemoryRecord,
    ReusablePatternRecord,
    ReusablePatternRegistry,
    SpeculativeIntegrationCandidate,
    ValidationBoundary,
    WarmCacheRecord,
    WarmEnvironmentIdentity,
    summarize_telemetry,
)
from parallax_api.code.patching import SourcePatch
from parallax_api.code.worker_recovery import (
    RecoveryAction,
    StallClassification,
    WorkerStallEvidence,
    classify_stall,
)
from parallax_api.models import EngineeringRun
from parallax_api.validation.browser import (
    ProtectedBrowserValidationResult,
    ProtectedValidationStatus,
    VisualReviewOutcome,
    VisualReviewResult,
)

PROJECT = "project:wave3-reference"
OTHER_PROJECT = "project:other"
RUN = "run:wave3-reference"
SPEC_DB = "specdb:wave3-reference"
SPEC_DIGEST = "a" * 64
L0 = "src:" + "0" * 64
L1 = "src:" + "1" * 64
T0 = datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)


def _run() -> EngineeringRun:
    return EngineeringRun(
        id=RUN,
        conversation_id="conversation:wave3-reference",
        spec_id="P2-V0.16.5",
        project_id=PROJECT,
        work_specification_id=SPEC_DB,
        work_specification_revision=1,
        work_specification_digest=SPEC_DIGEST,
        state="VERIFY",
        revision=1,
    )


def _context() -> CorrectionContext:
    return CorrectionContext.from_run(
        _run(),
        plan_ref="spec:P2-V0.16.5",
        dependencies=("workstream:95", "workstream:96"),
    )


class MemoryStateStore:
    def __init__(self) -> None:
        self.state: CorrectionSessionState | None = None

    def load(self, *, run_id: str, session_id: str):
        if self.state is None:
            return None
        return self.state if self.state.run_id == run_id and self.state.session_id == session_id else None

    def save(self, *, run: EngineeringRun, state: CorrectionSessionState, expected_revision: int):
        if self.state is None:
            if expected_revision != 0 or state.revision != 0:
                raise CorrectionStateConflict("new state revision mismatch")
            self.state = replace(state, revision=1)
        else:
            if self.state.revision != expected_revision or state.revision != expected_revision:
                raise CorrectionStateConflict("state CAS mismatch")
            self.state = replace(state, revision=expected_revision + 1)
        return self.state


class Planner:
    def plan(self, context, *, lineage_id, defects):
        return CorrectionPlan(
            target_defect_ids=tuple(item.defect_id for item in defects),
            patches=(
                SourcePatch(
                    path="app.py",
                    expected_base_sha256="b" * 64,
                    unified_diff="@@ -1 +1 @@\n-old\n+new\n",
                ),
            ),
            estimated_changed_bytes=8,
            compute_units=1,
        )


class Mutation:
    def __init__(self) -> None:
        self.calls = 0

    def apply(self, context, *, operation_key, base_lineage_id, plan):
        self.calls += 1
        return CorrectionMutationResult(
            lineage_id=L1,
            changed_bytes=8,
            replayed=False,
            evidence_ref="mutation:wave3-reference",
        )


class Validator:
    def __init__(self, initial: CandidateValidation) -> None:
        self.initial = initial
        self.calls: list[str] = []

    def validate(self, context, *, lineage_id):
        self.calls.append(lineage_id)
        if lineage_id == L0:
            return self.initial
        return CandidateValidation(
            project_id=PROJECT,
            run_id=RUN,
            work_specification_digest=SPEC_DIGEST,
            lineage_id=L1,
            quality=ProtectedQualityVector(0, 0, 0, 0, 0),
            defects=(),
            evidence_refs=("validation:fresh-corrected-lineage",),
            preview_deployment_id="dpl_wave3_corrected",
        )


def test_browser_failure_enters_existing_correction_and_only_fresh_exact_lineage_can_pass() -> None:
    browser = ProtectedBrowserValidationResult(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_digest=SPEC_DIGEST,
        lineage_id=L0,
        preview_deployment_id="dpl_wave3_defective",
        workflow_id="reference-app-primary",
        workflow_version=1,
        status=ProtectedValidationStatus.FAIL,
        deterministic_defects=("LAYOUT:VIEWPORT_OVERFLOW",),
        screenshot_differences=(),
        visual_reviews=(VisualReviewResult(VisualReviewOutcome.PASS, (), 0.99),),
        executions=(),
    )
    candidate = candidate_from_browser(browser)
    assert candidate.quality.deterministic_failures == 1
    assert candidate.quality.passed is False

    validator = Validator(candidate)
    mutation = Mutation()
    controller = AutonomousCorrectionController(
        run=_run(),
        context=_context(),
        planner=Planner(),
        mutation=mutation,
        validator=validator,
        state_store=MemoryStateStore(),
        budget=CorrectionBudgetPolicy(max_attempts=2),
    )
    state = controller.run(initial_lineage_id=L0)
    assert state.status is CorrectionSessionStatus.PASSED
    assert state.current_lineage_id == state.lkg_lineage_id == L1
    assert validator.calls == [L0, L1]
    assert mutation.calls == 1


def test_visual_review_cannot_override_deterministic_or_screenshot_failure() -> None:
    browser = ProtectedBrowserValidationResult(
        project_id=PROJECT,
        run_id=RUN,
        work_specification_digest=SPEC_DIGEST,
        lineage_id=L0,
        preview_deployment_id="dpl_wave3_defective",
        workflow_id="reference-app-primary",
        workflow_version=1,
        status=ProtectedValidationStatus.FAIL,
        deterministic_defects=(
            "SCREENSHOT_REGRESSION:mobile-390:primary",
            "NETWORK:REQUIRED_REQUEST_FAILED",
        ),
        screenshot_differences=(),
        visual_reviews=(VisualReviewResult(VisualReviewOutcome.PASS, (), 1.0),),
        executions=(),
    )
    candidate = candidate_from_browser(browser)
    assert candidate.quality.passed is False
    assert candidate.quality.screenshot_failures == 1
    assert candidate.quality.deterministic_failures == 1
    assert {item.source for item in candidate.defects} == {
        DefectSource.SCREENSHOT_REGRESSION,
        DefectSource.BROWSER_DETERMINISTIC,
    }


@pytest.mark.parametrize(
    ("evidence", "classification", "action", "human"),
    [
        (WorkerStallEvidence(provider_unavailable=True), StallClassification.PROVIDER_OUTAGE, RecoveryAction.BACKOFF_RETRY, False),
        (WorkerStallEvidence(rate_limited=True), StallClassification.RATE_LIMIT, RecoveryAction.BACKOFF_RETRY, False),
        (WorkerStallEvidence(credential_failure=True, credential_refreshable=True), StallClassification.CREDENTIAL_AUTHORIZATION, RecoveryAction.REFRESH_CREDENTIAL, False),
        (WorkerStallEvidence(credential_failure=True), StallClassification.CREDENTIAL_AUTHORIZATION, RecoveryAction.HUMAN_REQUIRED, True),
        (WorkerStallEvidence(material_specification_ambiguity=True), StallClassification.HUMAN_AUTHORITY_SPECIFICATION, RecoveryAction.HUMAN_REQUIRED, True),
    ],
)
def test_provider_recovery_and_human_boundaries_remain_distinct(evidence, classification, action, human) -> None:
    decision = classify_stall(evidence)
    assert decision.classification is classification
    assert decision.action is action
    assert decision.human_required is human


def _impact_graph() -> ChangeImpactGraph:
    return ChangeImpactGraph(
        version="wave3-reference-v1",
        rules=(
            ImpactRule(
                "services/api/**",
                ("component:api",),
                ("contract:api",),
                ("platform:api",),
                ("check:api",),
            ),
        ),
        global_invariants=("check:global",),
        full_suite_checks=("check:global", "check:api", "check:browser", "check:promotion"),
    )


def test_optimization_stays_non_authoritative_and_full_promotion_boundaries_cannot_be_skipped() -> None:
    graph = _impact_graph()
    unknown = graph.select(("unmapped/new-area.txt",), boundary=ValidationBoundary.DEVELOPMENT_FAST)
    assert unknown.conservative is True
    assert set(unknown.selected_checks) == set(graph.full_suite_checks)
    for boundary in (
        ValidationBoundary.WORKER_ACCEPTANCE,
        ValidationBoundary.INTEGRATION_ACCEPTANCE,
        ValidationBoundary.RELEASE_PROMOTION,
    ):
        selection = graph.select(("services/api/parallax_api/main.py",), boundary=boundary)
        assert selection.conservative is True
        assert set(selection.selected_checks) == set(graph.full_suite_checks)

    speculative = SpeculativeIntegrationCandidate.build(
        project_id=PROJECT,
        lineage_refs=(L0, L1),
        validation_refs=("validation:speculative",),
    )
    assert speculative.authoritative is False
    assert speculative.to_record()["authoritative"] is False

    identity = WarmEnvironmentIdentity.build(
        runtime="python313",
        operating_system="linux",
        architecture="x86_64",
        toolchain_digest="1" * 64,
        dependency_digest="2" * 64,
        configuration_digest="3" * 64,
        source_digest="4" * 64,
        cache_schema_version="v1",
    )
    assert WarmCacheRecord(
        identity.digest,
        False,
        ("cache:provenance-incomplete",),
    ).eligible_for(identity) is False


def test_project_private_pattern_repair_memory_and_telemetry_cannot_cross_project_or_leak_secrets() -> None:
    pattern = ReusablePatternRecord(
        "pattern:private",
        "v1",
        "5" * 64,
        "component",
        ("python313",),
        ("validation:pattern",),
        True,
        project_id=PROJECT,
    )
    registry = ReusablePatternRegistry((pattern,))
    assert registry.recommend(
        project_id=PROJECT,
        pattern_type="component",
        compatibility=("python313",),
    ) == (pattern,)
    assert registry.recommend(
        project_id=OTHER_PROJECT,
        pattern_type="component",
        compatibility=("python313",),
    ) == ()

    repair = RepairMemoryRecord(
        "6" * 64,
        "repair:layout",
        "passed",
        ("python313",),
        ("validation:repair",),
        project_id=PROJECT,
    )
    memory = RepairMemory((repair,))
    assert memory.recommend(
        project_id=OTHER_PROJECT,
        fingerprint="6" * 64,
        compatibility=("python313",),
    ) == ()

    observations = (
        PhaseObservation(PROJECT, RUN, "ws:99", DevelopmentPhase.GENERATION, T0, T0 + timedelta(seconds=2), 0, "passed"),
        PhaseObservation(PROJECT, RUN, "ws:99", DevelopmentPhase.RETRY, T0 + timedelta(seconds=2), T0 + timedelta(seconds=3), 1, "complete"),
        PhaseObservation(PROJECT, RUN, "ws:99", DevelopmentPhase.STALL, T0 + timedelta(seconds=3), T0 + timedelta(seconds=5), 1, "recovered", critical_path_blocked=True),
        PhaseObservation(PROJECT, RUN, "ws:99", DevelopmentPhase.INTEGRATION, T0 + timedelta(seconds=5), T0 + timedelta(seconds=7), 1, "passed", critical_path_blocked=True),
    )
    summary = summarize_telemetry(observations)
    assert summary.validated_outcome_lead_ms == 7000
    assert summary.retry_ms == 1000
    assert summary.stall_ms == 2000
    assert summary.integration_wait_ms == 2000
    with pytest.raises(OptimizationPolicyError, match="across Projects"):
        summarize_telemetry(
            (observations[0], replace(observations[1], project_id=OTHER_PROJECT))
        )
    with pytest.raises(OptimizationPolicyError):
        PhaseObservation(
            PROJECT,
            RUN,
            "ws:99",
            DevelopmentPhase.TEST,
            T0,
            T0 + timedelta(seconds=1),
            0,
            "failed",
            evidence_refs=("secret:abcdefgh",),
        )
