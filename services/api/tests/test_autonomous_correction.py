from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from parallax_api.code.autonomous_correction import (
    AutonomousCorrectionController,
    CandidateValidation,
    CorrectionBoundary,
    CorrectionBudgetPolicy,
    CorrectionContext,
    CorrectionMutationResult,
    CorrectionPathPolicy,
    CorrectionPlan,
    CorrectionPolicyError,
    CorrectionReplayConflict,
    CorrectionSessionState,
    CorrectionSessionStatus,
    CorrectionStateConflict,
    CorrectionStopReason,
    DefectPrecedence,
    DefectSeverity,
    DefectSource,
    FailureDispatch,
    NormalizedDefect,
    ProtectedQualityVector,
    VisualDisposition,
    WorkerCorrectionCheckpointSink,
    candidate_from_browser,
    normalize_failure,
)
from parallax_api.code.patching import SourcePatch
from parallax_api.code.worker_recovery import WorkerLease, WorkerLifecycleState
from parallax_api.models import EngineeringRun
from parallax_api.validation.browser import (
    ProtectedBrowserValidationResult,
    ProtectedValidationStatus,
    VisualFinding,
    VisualReviewOutcome,
    VisualReviewResult,
)


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
SPEC_DB_ID = "33333333-3333-4333-8333-333333333333"
CONVERSATION_ID = "44444444-4444-4444-8444-444444444444"
SPEC_DIGEST = "a" * 64
PLAN_REF = "plan:P2-V0.16.3:compiled"
L0 = "src:" + "0" * 64
L1 = "src:" + "1" * 64
L2 = "src:" + "2" * 64


def _run() -> EngineeringRun:
    return EngineeringRun(
        id=RUN_ID,
        conversation_id=CONVERSATION_ID,
        spec_id="P2-V0.16.3",
        project_id=PROJECT_ID,
        work_specification_id=SPEC_DB_ID,
        work_specification_revision=4,
        work_specification_digest=SPEC_DIGEST,
        state="VERIFY",
        revision=8,
    )


def _context(run: EngineeringRun | None = None) -> CorrectionContext:
    return CorrectionContext.from_run(
        run or _run(),
        plan_ref=PLAN_REF,
        dependencies=("workstream:95", "workstream:96"),
    )


def _defect(
    lineage: str,
    *,
    code: str = "TEST_FAILURE",
    source: DefectSource = DefectSource.TEST,
    precedence: DefectPrecedence = DefectPrecedence.DETERMINISTIC,
    boundary: CorrectionBoundary | None = None,
    visual: VisualDisposition | None = None,
    path: str | None = "app.py",
) -> NormalizedDefect:
    return normalize_failure(
        source=source,
        precedence=precedence,
        failure_code=code,
        severity=DefectSeverity.ERROR,
        reproducible=True,
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        work_specification_digest=SPEC_DIGEST,
        lineage_id=lineage,
        evidence_refs=(f"evidence:{code.lower()}",),
        source_path=path,
        boundary=boundary,
        visual_disposition=visual,
    )


def _candidate(
    lineage: str,
    defects: tuple[NormalizedDefect, ...],
    *,
    evidence: str | None = None,
) -> CandidateValidation:
    return CandidateValidation(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        work_specification_digest=SPEC_DIGEST,
        lineage_id=lineage,
        quality=ProtectedQualityVector.from_defects(defects),
        defects=defects,
        evidence_refs=(evidence or f"validation:{lineage[-6:]}",),
    )


def _pass(lineage: str) -> CandidateValidation:
    return _candidate(lineage, ())


class MemoryStateStore:
    def __init__(self) -> None:
        self.states: dict[tuple[str, str], CorrectionSessionState] = {}

    def load(self, *, run_id: str, session_id: str) -> CorrectionSessionState | None:
        return self.states.get((run_id, session_id))

    def save(
        self,
        *,
        run: EngineeringRun,
        state: CorrectionSessionState,
        expected_revision: int,
    ) -> CorrectionSessionState:
        key = (run.id, state.session_id)
        existing = self.states.get(key)
        if existing is None:
            if expected_revision != 0 or state.revision != 0:
                raise CorrectionStateConflict("new state revision mismatch")
            saved = replace(state, revision=1)
        else:
            if existing.revision != expected_revision or state.revision != expected_revision:
                raise CorrectionStateConflict("state CAS mismatch")
            saved = replace(state, revision=expected_revision + 1)
        self.states[key] = saved
        return saved


class MappingValidator:
    def __init__(self, values: dict[str, CandidateValidation]) -> None:
        self.values = values
        self.calls: list[str] = []

    def validate(self, context: CorrectionContext, *, lineage_id: str) -> CandidateValidation:
        self.calls.append(lineage_id)
        return self.values[lineage_id]


class StandardPlanner:
    def __init__(
        self,
        *,
        boundary: CorrectionBoundary | None = None,
        changed: int = 32,
        compute: int = 1,
    ) -> None:
        self.boundary = boundary
        self.changed = changed
        self.compute = compute
        self.calls = 0

    def plan(
        self,
        context: CorrectionContext,
        *,
        lineage_id: str,
        defects: tuple[NormalizedDefect, ...],
    ) -> CorrectionPlan:
        self.calls += 1
        targets = tuple(item.defect_id for item in defects)
        if self.boundary is not None:
            return CorrectionPlan(
                target_defect_ids=targets,
                patches=(),
                estimated_changed_bytes=0,
                compute_units=0,
                boundary=self.boundary,
            )
        return CorrectionPlan(
            target_defect_ids=targets,
            patches=(
                SourcePatch(
                    path="app.py",
                    expected_base_sha256="b" * 64,
                    unified_diff="@@ -1,1 +1,1 @@\n-old\n+new\n",
                ),
            ),
            estimated_changed_bytes=self.changed,
            compute_units=self.compute,
        )


class ReplayMutation:
    def __init__(
        self,
        lineages: list[str],
        *,
        changed_bytes: int = 24,
        crash_after_first_store: bool = False,
    ) -> None:
        self.lineages = list(lineages)
        self.changed_bytes = changed_bytes
        self.crash_after_first_store = crash_after_first_store
        self.records: dict[str, CorrectionMutationResult] = {}
        self.calls: list[tuple[str, str]] = []
        self.unique_mutations = 0
        self._crashed = False

    def apply(
        self,
        context: CorrectionContext,
        *,
        operation_key: str,
        base_lineage_id: str,
        plan: CorrectionPlan,
    ) -> CorrectionMutationResult:
        self.calls.append((operation_key, base_lineage_id))
        if operation_key in self.records:
            return replace(self.records[operation_key], replayed=True)
        lineage = self.lineages.pop(0)
        result = CorrectionMutationResult(
            lineage_id=lineage,
            changed_bytes=self.changed_bytes,
            replayed=False,
            evidence_ref=f"mutation:{lineage[-6:]}",
        )
        self.records[operation_key] = result
        self.unique_mutations += 1
        if self.crash_after_first_store and not self._crashed:
            self._crashed = True
            raise SimulatedProcessLoss("process disappeared after durable mutation acceptance")
        return result


class SimulatedProcessLoss(RuntimeError):
    pass


def _controller(
    *,
    validator: MappingValidator,
    mutation: ReplayMutation,
    planner: StandardPlanner | None = None,
    store: MemoryStateStore | None = None,
    budget: CorrectionBudgetPolicy | None = None,
    now=None,
    checkpoint_sink=None,
) -> AutonomousCorrectionController:
    run = _run()
    return AutonomousCorrectionController(
        run=run,
        context=_context(run),
        planner=planner or StandardPlanner(),
        mutation=mutation,
        validator=validator,
        state_store=store or MemoryStateStore(),
        budget=budget,
        checkpoint_sink=checkpoint_sink,
        now=now,
    )


def test_quality_vector_enforces_exact_protected_precedence() -> None:
    assert ProtectedQualityVector(0, 99, 99, 99, 99) < ProtectedQualityVector(1, 0, 0, 0, 0)
    assert ProtectedQualityVector(0, 0, 0, 99, 99) < ProtectedQualityVector(0, 1, 0, 0, 0)
    assert ProtectedQualityVector(0, 0, 0, 1, 0) < ProtectedQualityVector(0, 0, 1, 0, 0)
    assert ProtectedQualityVector(0, 0, 0, 0, 0).passed is True


def test_normalized_defects_cover_supported_sources_and_reject_sensitive_evidence() -> None:
    for source in DefectSource:
        defect = _defect(L0, source=source)
        assert defect.source is source
        assert defect.project_id == PROJECT_ID
        assert defect.lineage_id == L0
        assert defect.defect_id.startswith("defect:")

    with pytest.raises(CorrectionPolicyError, match="secret-bearing"):
        normalize_failure(
            source=DefectSource.PROVIDER,
            precedence=DefectPrecedence.DETERMINISTIC,
            failure_code="AUTH_FAILURE",
            severity=DefectSeverity.ERROR,
            reproducible=True,
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            work_specification_digest=SPEC_DIGEST,
            lineage_id=L0,
            evidence_refs=("authorization:abcdefghijklmnop",),
        )

    with pytest.raises(CorrectionPolicyError, match="private-reasoning"):
        normalize_failure(
            source=DefectSource.IMPLEMENT,
            precedence=DefectPrecedence.DETERMINISTIC,
            failure_code="MODEL_FAILURE",
            severity=DefectSeverity.ERROR,
            reproducible=True,
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            work_specification_digest=SPEC_DIGEST,
            lineage_id=L0,
            evidence_refs=("scratchpad:internal",),
        )


def test_browser_result_is_consumed_as_normalized_boundary() -> None:
    result = ProtectedBrowserValidationResult(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        work_specification_digest=SPEC_DIGEST,
        lineage_id=L0,
        preview_deployment_id="dpl_preview_1",
        workflow_id="reference-app-primary",
        workflow_version=1,
        status=ProtectedValidationStatus.FAIL,
        deterministic_defects=(
            "LAYOUT:VIEWPORT_OVERFLOW",
            "SCREENSHOT_REGRESSION:mobile-390:primary",
        ),
        screenshot_differences=(),
        visual_reviews=(
            VisualReviewResult(
                VisualReviewOutcome.REVIEW,
                (VisualFinding("SPACING", "hero", "Spacing needs review"),),
                0.8,
            ),
        ),
        executions=(),
    )

    candidate = candidate_from_browser(result)

    assert candidate.preview_deployment_id == "dpl_preview_1"
    assert candidate.quality == ProtectedQualityVector(1, 0, 1, 0, 1)
    assert {item.source for item in candidate.defects} == {
        DefectSource.BROWSER_DETERMINISTIC,
        DefectSource.SCREENSHOT_REGRESSION,
        DefectSource.VISUAL,
    }


@pytest.mark.parametrize(
    "path",
    [
        "specs/P2-V0.16.3.md",
        ".github/workflows/release.yml",
        "PROJECT-CONSTITUTION.md",
        "ARCHITECTURE.md",
        "CURRENT-STATE.md",
        "services/api/parallax_api/intelligence/protected_metrics.py",
        "services/api/parallax_api/tools/registry.py",
        "services/api/parallax_api/validation/browser.py",
    ],
)
def test_correction_cannot_mutate_protected_policy_authority_or_browser_contract(path: str) -> None:
    patch = SourcePatch(path=path, expected_base_sha256="c" * 64, unified_diff="@@ -1 +1 @@\n-a\n+b\n")
    with pytest.raises(CorrectionPolicyError, match="protected policy or authority"):
        CorrectionPathPolicy().validate(patch)


def test_multi_attempt_correction_converges_and_advances_lkg_only_on_improvement() -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0, code="TEST_FAILURE"), _defect(L0, code="LAYOUT_FAILURE"))),
            L1: _candidate(L1, (_defect(L1, code="TEST_FAILURE"),)),
            L2: _pass(L2),
        }
    )
    mutation = ReplayMutation([L1, L2])
    state = _controller(validator=validator, mutation=mutation).run(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.PASSED
    assert state.attempt_count == 2
    assert state.current_lineage_id == state.lkg_lineage_id == L2
    assert state.current_quality.passed
    assert validator.calls == [L0, L1, L2]
    assert [base for _, base in mutation.calls] == [L0, L1]


def test_regression_does_not_replace_lkg() -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0, code="ACCEPTANCE_FAILURE", precedence=DefectPrecedence.PROTECTED_ACCEPTANCE),)),
            L1: _candidate(L1, (_defect(L1, code="NEW_TEST_FAILURE"),)),
        }
    )
    state = _controller(validator=validator, mutation=ReplayMutation([L1])).advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.ACTIVE
    assert state.current_lineage_id == state.lkg_lineage_id == L0
    assert state.current_quality == ProtectedQualityVector(0, 1, 0, 0, 0)
    assert state.no_progress_count == 1


def test_equal_quality_is_no_progress() -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0, code="A"),)),
            L1: _candidate(L1, (_defect(L1, code="B"),)),
        }
    )
    state = _controller(
        validator=validator,
        mutation=ReplayMutation([L1]),
        budget=CorrectionBudgetPolicy(max_no_progress=0),
    ).advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.STOPPED
    assert state.stop_reason is CorrectionStopReason.NO_PROGRESS
    assert state.lkg_lineage_id == L0


def test_equivalent_defect_repeat_bound_stops_churn() -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0, code="SAME_FAILURE"),)),
            L1: _candidate(L1, (_defect(L1, code="SAME_FAILURE"),)),
        }
    )
    state = _controller(
        validator=validator,
        mutation=ReplayMutation([L1]),
        budget=CorrectionBudgetPolicy(max_defect_repeats=1, max_no_progress=10),
    ).advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.STOPPED
    assert state.stop_reason is CorrectionStopReason.REPEATED_DEFECT
    assert state.attempt_count == 1


def test_a_b_a_oscillation_is_detected_from_candidate_history() -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0, code="A"),)),
            L1: _candidate(L1, (_defect(L1, code="B"),)),
            L2: _candidate(L2, (_defect(L2, code="A"),)),
        }
    )
    controller = _controller(
        validator=validator,
        mutation=ReplayMutation([L1, L2]),
        budget=CorrectionBudgetPolicy(max_oscillations=0, max_no_progress=10, max_defect_repeats=10),
    )

    assert controller.advance(initial_lineage_id=L0).status is CorrectionSessionStatus.ACTIVE
    state = controller.advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.STOPPED
    assert state.stop_reason is CorrectionStopReason.OSCILLATION
    assert state.oscillation_count == 1


@pytest.mark.parametrize(
    ("budget", "planner", "mutation_changed"),
    [
        (CorrectionBudgetPolicy(max_attempts=1, max_no_progress=10), StandardPlanner(), 24),
        (CorrectionBudgetPolicy(max_changed_bytes=20, max_no_progress=10), StandardPlanner(changed=10), 25),
        (CorrectionBudgetPolicy(max_compute_units=1, max_no_progress=10), StandardPlanner(compute=2), 24),
    ],
)
def test_attempt_churn_and_compute_budgets_stop_resource_exhaustion(
    budget: CorrectionBudgetPolicy,
    planner: StandardPlanner,
    mutation_changed: int,
) -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0, code="A"),)),
            L1: _candidate(L1, (_defect(L1, code="B"),)),
        }
    )
    state = _controller(
        validator=validator,
        mutation=ReplayMutation([L1], changed_bytes=mutation_changed),
        planner=planner,
        budget=budget,
    ).advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.STOPPED
    assert state.stop_reason is CorrectionStopReason.RESOURCE_EXHAUSTION


def test_elapsed_runtime_budget_stops_before_mutation() -> None:
    base = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    clock = iter(
        (
            base,
            base,
            base + timedelta(seconds=6),
            base + timedelta(seconds=6),
            base + timedelta(seconds=6),
        )
    )
    validator = MappingValidator({L0: _candidate(L0, (_defect(L0, code="A"),))})
    mutation = ReplayMutation([L1])
    state = _controller(
        validator=validator,
        mutation=mutation,
        budget=CorrectionBudgetPolicy(max_elapsed_seconds=5),
        now=lambda: next(clock),
    ).advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.STOPPED
    assert state.stop_reason is CorrectionStopReason.RESOURCE_EXHAUSTION
    assert mutation.unique_mutations == 0


@pytest.mark.parametrize(
    ("boundary", "reason"),
    [
        (CorrectionBoundary.HUMAN_APPROVAL, CorrectionStopReason.HUMAN_APPROVAL_REQUIRED),
        (CorrectionBoundary.PRIVILEGED_ACTION, CorrectionStopReason.PRIVILEGED_BOUNDARY),
        (CorrectionBoundary.SPEC_AMBIGUITY, CorrectionStopReason.MATERIAL_SPEC_AMBIGUITY),
        (CorrectionBoundary.CREDENTIAL_AUTHORIZATION, CorrectionStopReason.MISSING_CREDENTIAL_AUTHORIZATION),
        (CorrectionBoundary.PROTECTED_POLICY_CHANGE, CorrectionStopReason.PROTECTED_POLICY_BOUNDARY),
        (CorrectionBoundary.UNSUPPORTED_REPAIR, CorrectionStopReason.UNRECOVERABLE_FAILURE),
    ],
)
def test_human_privilege_spec_credential_policy_and_unsupported_boundaries_fail_closed(
    boundary: CorrectionBoundary,
    reason: CorrectionStopReason,
) -> None:
    validator = MappingValidator({L0: _candidate(L0, (_defect(L0, code="BOUNDARY", boundary=boundary),))})
    planner = StandardPlanner()
    mutation = ReplayMutation([L1])
    state = _controller(validator=validator, mutation=mutation, planner=planner).advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.STOPPED
    assert state.stop_reason is reason
    assert planner.calls == 0
    assert mutation.unique_mutations == 0


def test_planner_boundary_stops_without_source_mutation() -> None:
    validator = MappingValidator({L0: _candidate(L0, (_defect(L0),))})
    mutation = ReplayMutation([L1])
    state = _controller(
        validator=validator,
        mutation=mutation,
        planner=StandardPlanner(boundary=CorrectionBoundary.HUMAN_APPROVAL),
    ).advance(initial_lineage_id=L0)

    assert state.stop_reason is CorrectionStopReason.HUMAN_APPROVAL_REQUIRED
    assert mutation.unique_mutations == 0


def test_process_recreation_reuses_pending_operation_key_without_duplicate_mutation() -> None:
    validator = MappingValidator({L0: _candidate(L0, (_defect(L0, code="REPAIR_ME"),)), L1: _pass(L1)})
    store = MemoryStateStore()
    planner = StandardPlanner()
    mutation = ReplayMutation([L1], crash_after_first_store=True)
    first = _controller(validator=validator, mutation=mutation, planner=planner, store=store)

    with pytest.raises(SimulatedProcessLoss):
        first.advance(initial_lineage_id=L0)

    durable = store.load(run_id=RUN_ID, session_id=_context().session_id)
    assert durable is not None and durable.pending_operation_key is not None
    pending_key = durable.pending_operation_key
    assert durable.attempt_count == 0
    assert mutation.unique_mutations == 1

    recreated = _controller(validator=validator, mutation=mutation, planner=planner, store=store)
    state = recreated.advance(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.PASSED
    assert mutation.unique_mutations == 1
    assert len(mutation.calls) == 2
    assert mutation.calls[0][0] == mutation.calls[1][0] == pending_key
    assert state.pending_operation_key is None
    assert state.current_lineage_id == L1


def test_recreated_planner_mismatch_fails_closed() -> None:
    validator = MappingValidator({L0: _candidate(L0, (_defect(L0),)), L1: _pass(L1)})
    store = MemoryStateStore()
    mutation = ReplayMutation([L1], crash_after_first_store=True)
    first = _controller(validator=validator, mutation=mutation, planner=StandardPlanner(), store=store)
    with pytest.raises(SimulatedProcessLoss):
        first.advance(initial_lineage_id=L0)

    recreated = _controller(
        validator=validator,
        mutation=mutation,
        planner=StandardPlanner(changed=999),
        store=store,
    )
    with pytest.raises(CorrectionReplayConflict):
        recreated.advance(initial_lineage_id=L0)
    assert mutation.unique_mutations == 1


def test_fresh_validation_must_match_returned_lineage() -> None:
    validator = MappingValidator(
        {
            L0: _candidate(L0, (_defect(L0),)),
            L1: _candidate(L2, (_defect(L2),)),
        }
    )
    with pytest.raises(Exception, match="fresh validation result"):
        _controller(validator=validator, mutation=ReplayMutation([L1])).advance(initial_lineage_id=L0)


def test_failure_dispatch_is_data_only_and_exactly_bound() -> None:
    validator = MappingValidator(
        {L0: _candidate(L0, (_defect(L0, boundary=CorrectionBoundary.SPEC_AMBIGUITY),))}
    )
    controller = _controller(validator=validator, mutation=ReplayMutation([L1]))
    dispatch = controller.dispatch(
        controller.advance(initial_lineage_id=L0),
        receiving_class="integration-repair",
    )

    assert isinstance(dispatch, FailureDispatch)
    assert dispatch.project_id == PROJECT_ID
    assert dispatch.run_id == RUN_ID
    assert dispatch.source_lineage_id == dispatch.lkg_lineage_id == L0
    assert dispatch.dependency_refs == ("workstream:95", "workstream:96")
    assert dispatch.stop_reason is CorrectionStopReason.MATERIAL_SPEC_AMBIGUITY
    assert dispatch.reproducible is True
    assert not hasattr(dispatch, "github_issue")
    assert not hasattr(dispatch, "provider_action")
    assert not hasattr(dispatch, "deployment")


def test_worker_checkpoint_sink_reuses_existing_worker_identity() -> None:
    class FakeWorkerService:
        def __init__(self) -> None:
            self.calls = []

        def checkpoint(self, lease, checkpoint, **kwargs):
            self.calls.append((lease, checkpoint, kwargs))
            return object()

    run = _run()
    service = FakeWorkerService()
    lease = WorkerLease(
        execution_id="worker-execution-1",
        run_id=RUN_ID,
        owner_id="worker-owner-1",
        generation=7,
        expires_at=datetime(2026, 8, 23, 20, 0, tzinfo=timezone.utc),
    )
    sink = WorkerCorrectionCheckpointSink(service, lease=lease, run=run, context=_context(run))
    state = _controller(
        validator=MappingValidator({L0: _pass(L0)}),
        mutation=ReplayMutation([]),
        checkpoint_sink=sink,
    ).run(initial_lineage_id=L0)

    assert state.status is CorrectionSessionStatus.PASSED
    assert len(service.calls) == 1
    used_lease, checkpoint, kwargs = service.calls[0]
    assert used_lease is lease
    assert checkpoint.source_lineage_ref == L0
    assert checkpoint.last_known_good_lineage_ref == L0
    assert checkpoint.plan_ref == PLAN_REF
    assert kwargs["authoritative_source_lineage_ref"] == L0
    assert kwargs["state"] is WorkerLifecycleState.SUCCEEDED


def test_plan_surface_has_no_generic_execution_provider_or_policy_controls() -> None:
    plan = StandardPlanner().plan(_context(), lineage_id=L0, defects=(_defect(L0),))
    assert plan.patches[0].path == "app.py"
    for forbidden in (
        "command",
        "shell",
        "url",
        "headers",
        "cookies",
        "environment",
        "provider_target",
        "evaluator_threshold",
        "acceptance_criteria",
        "browser_baseline",
        "production_action",
    ):
        assert not hasattr(plan, forbidden)


def test_state_store_cas_contract_rejects_stale_revision() -> None:
    store = MemoryStateStore()
    controller = _controller(
        validator=MappingValidator({L0: _candidate(L0, (_defect(L0),))}),
        mutation=ReplayMutation([L1]),
        store=store,
    )
    state = controller._initialize(L0)
    stale = state
    saved = store.save(run=_run(), state=state, expected_revision=state.revision)
    assert saved.revision == state.revision + 1
    with pytest.raises(CorrectionStateConflict, match="CAS"):
        store.save(run=_run(), state=stale, expected_revision=stale.revision)
