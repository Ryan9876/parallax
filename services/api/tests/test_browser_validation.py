from __future__ import annotations

from dataclasses import replace

import pytest

from parallax_api.code.source_delivery_composition import ProviderActionAuditPair, VerifiedDeliveryResult
from parallax_api.models import EngineeringRun
from parallax_api.tools.contracts import ToolAuditRecord, ToolConsequence, ToolOutcome
from parallax_api.tools.providers import ProviderActionEvidence, ProviderActionState, VercelPreviewStatus
from parallax_api.validation.browser import (
    AccessibilityFinding,
    AccessibilityImpact,
    AssertionEvidence,
    BrowserAction,
    BrowserActionKind,
    BrowserExecutionEvidence,
    BrowserExecutionRequest,
    BrowserTargetResolver,
    BrowserValidationError,
    BrowserWorkflow,
    BrowserWorkflowRegistry,
    ConsoleFinding,
    LayoutFinding,
    NETWORK_POLICY_EXACT_PREVIEW,
    NetworkFinding,
    ProtectedBrowserValidator,
    ProtectedValidationStatus,
    ScreenshotArtifact,
    ScreenshotBaseline,
    ScreenshotBaselineRegistry,
    ScreenshotDifference,
    SemanticTarget,
    SemanticTargetKind,
    VisualFinding,
    VisualReviewOutcome,
    VisualReviewResult,
    reference_app_workflow,
    validate_execution_evidence,
    validate_screenshot_difference,
)
from parallax_api.validation.sandbox_browser import VercelSandboxBrowserExecutor


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT_ID = "22222222-2222-4222-8222-222222222222"
RUN_ID = "33333333-3333-4333-8333-333333333333"
SPEC_ID = "44444444-4444-4444-8444-444444444444"
LINEAGE_ID = "src:" + "a" * 64
CONTENT_DIGEST = "b" * 64
SPEC_DIGEST = "c" * 64
REPOSITORY_DIGEST = "d" * 64
PREVIEW_ID = "dpl_preview_1"
PREVIEW_URL = "https://parallax-preview.vercel.app"


class FakeDeliveryStore:
    def __init__(self, payload: dict[str, object] | None) -> None:
        self.payload = payload
        self.loads: list[tuple[str, str]] = []
        self.persist_calls = 0

    def load(self, *, run_id: str, lineage_id: str) -> dict[str, object] | None:
        self.loads.append((run_id, lineage_id))
        return self.payload

    def persist(self, **_: object):
        self.persist_calls += 1
        raise AssertionError("browser validation must never persist or replay provider delivery")


def _run(**changes: object) -> EngineeringRun:
    values: dict[str, object] = {
        "id": RUN_ID,
        "conversation_id": "55555555-5555-4555-8555-555555555555",
        "spec_id": "P2-V0.16.2",
        "project_id": PROJECT_ID,
        "work_specification_id": SPEC_ID,
        "work_specification_revision": 3,
        "work_specification_digest": SPEC_DIGEST,
        "state": "VERIFY",
    }
    values.update(changes)
    return EngineeringRun(**values)


def _delivery(
    *,
    project_id: str = PROJECT_ID,
    lineage_id: str = LINEAGE_ID,
    preview_status: str = VercelPreviewStatus.READY.value,
    preview_url: str | None = PREVIEW_URL,
) -> VerifiedDeliveryResult:
    evidence = ProviderActionEvidence(
        provider="vercel",
        action="preview.read",
        state=ProviderActionState.SUCCEEDED,
        project_ref=project_id,
        repository_identity_digest=REPOSITORY_DIGEST,
        source_revision="abc123",
        lineage_id=lineage_id,
        lineage_digest=CONTENT_DIGEST,
        result_identity=PREVIEW_ID,
        result_status=preview_status,
        safe_url=PREVIEW_URL,
    )
    audit = ToolAuditRecord(
        request_id="request:preview-read",
        capability_id="capability:preview-read",
        project_ref=project_id,
        tool="vercel",
        action="preview.read",
        actor_ref="actor:test",
        consequence=ToolConsequence.READ,
        authority_allowed=True,
        outcome=ToolOutcome.SUCCEEDED,
        deny_reason=None,
        approval_id=None,
        request_digest="e" * 64,
        result_digest="f" * 64,
        result_code=preview_status,
        result_identity=PREVIEW_ID,
    )
    return VerifiedDeliveryResult(
        project_id=project_id,
        run_id=RUN_ID,
        repository_identity_digest=REPOSITORY_DIGEST,
        lineage_id=lineage_id,
        content_digest=CONTENT_DIGEST,
        branch_name="parallax/reference",
        commit_revision="abc123",
        pull_request_number=123,
        pull_request_url="https://github.com/Ryan9876/parallax/pull/123",
        preview_deployment_id=PREVIEW_ID,
        preview_status=preview_status,
        preview_url=preview_url,
        actions=(ProviderActionAuditPair(evidence=evidence, audit=audit),),
    )


def _resolver(delivery: VerifiedDeliveryResult | None = None) -> tuple[BrowserTargetResolver, FakeDeliveryStore]:
    payload = (delivery or _delivery()).to_record()
    store = FakeDeliveryStore(payload)
    return BrowserTargetResolver(store), store


def _hash_for_viewport(viewport_id: str) -> str:
    return ("1" if viewport_id == "mobile-390" else "2") * 64


def _screenshot(request: BrowserExecutionRequest, *, sha256: str | None = None) -> ScreenshotArtifact:
    target = request.target
    return ScreenshotArtifact(
        project_id=target.project_id,
        run_id=target.run_id,
        work_specification_digest=target.work_specification_digest,
        lineage_id=target.lineage_id,
        preview_deployment_id=target.preview_deployment_id,
        workflow_id=request.workflow.workflow_id,
        workflow_version=request.workflow.version,
        viewport_id=request.viewport.viewport_id,
        checkpoint="primary",
        artifact_ref=f"artifact:{request.viewport.viewport_id}:primary",
        sha256=sha256 or _hash_for_viewport(request.viewport.viewport_id),
        width=request.viewport.width,
        height=request.viewport.height,
    )


class ScenarioExecutor:
    def __init__(self, scenario: str = "pass") -> None:
        self.scenario = scenario
        self.requests: list[BrowserExecutionRequest] = []

    def execute(self, request: BrowserExecutionRequest) -> BrowserExecutionEvidence:
        self.requests.append(request)
        assertions: tuple[AssertionEvidence, ...] = (
            AssertionEvidence("HEADING_VISIBLE", self.scenario != "semantic", "role:heading:Parallax"),
        )
        accessibility = ()
        console = ()
        network = ()
        layout = ()
        if self.scenario == "a11y":
            accessibility = (AccessibilityFinding("button-name", AccessibilityImpact.SERIOUS, "test_id:submit", 1),)
        if self.scenario == "console":
            console = (ConsoleFinding("PAGE_ERROR", "ReferenceError: component failed"),)
        if self.scenario == "network":
            network = (
                NetworkFinding("GET", request.allowed_host, "/p2-api/state", status=500, required=True),
            )
        if self.scenario == "external":
            network = (
                NetworkFinding("GET", "evil.example", "/collect", failure_class="BLOCKED", unexpected_external=True),
            )
        if self.scenario == "overflow":
            layout = (LayoutFinding("VIEWPORT_OVERFLOW", "test_id:parallax-root", 0, 0, 1600, 900),)
        if self.scenario == "overlay":
            layout = (LayoutFinding("BLOCKING_OVERLAY", "test_id:modal", 0, 0, 390, 844),)
        return BrowserExecutionEvidence(
            project_id=request.target.project_id,
            run_id=request.target.run_id,
            lineage_id=request.target.lineage_id,
            preview_deployment_id=request.target.preview_deployment_id,
            workflow_id=request.workflow.workflow_id,
            workflow_version=request.workflow.version,
            viewport_id=request.viewport.viewport_id,
            network_policy=NETWORK_POLICY_EXACT_PREVIEW,
            assertions=assertions,
            accessibility=accessibility,
            console=console,
            network=network,
            layout=layout,
            screenshots=(_screenshot(request),),
        )


class FixedComparator:
    def __init__(self, ratio: float = 0.0) -> None:
        self.ratio = ratio
        self.calls = 0

    def compare(self, candidate: ScreenshotArtifact, baseline: ScreenshotBaseline) -> ScreenshotDifference:
        self.calls += 1
        return ScreenshotDifference(candidate.sha256, baseline.sha256, self.ratio)


class FixedReviewer:
    def __init__(self, outcome: VisualReviewOutcome = VisualReviewOutcome.PASS) -> None:
        self.outcome = outcome
        self.calls = 0

    def review(self, screenshot: ScreenshotArtifact, *, context: tuple[str, ...]) -> VisualReviewResult:
        self.calls += 1
        assert context == (
            "workflow:reference-app-primary:v1",
            "deterministic:PASS",
            "screenshot-regression:PASS",
        )
        findings = ()
        if self.outcome is not VisualReviewOutcome.PASS:
            findings = (VisualFinding("VISUAL_QUALITY", screenshot.viewport_id, "Spacing diverges from approved reference"),)
        return VisualReviewResult(self.outcome, findings, 0.92)


def _baselines(*, threshold: float = 0.05) -> ScreenshotBaselineRegistry:
    return ScreenshotBaselineRegistry(
        tuple(
            ScreenshotBaseline(
                project_id=PROJECT_ID,
                workflow_id="reference-app-primary",
                workflow_version=1,
                viewport_id=viewport_id,
                checkpoint="primary",
                design_state_id="editorial-optical-v1",
                artifact_ref=f"baseline:{viewport_id}:primary",
                sha256=_hash_for_viewport(viewport_id),
                max_difference_ratio=threshold,
            )
            for viewport_id in ("mobile-390", "desktop-1440")
        )
    )


def _validator(
    *,
    scenario: str = "pass",
    ratio: float = 0.0,
    visual: VisualReviewOutcome = VisualReviewOutcome.PASS,
):
    resolver, store = _resolver()
    executor = ScenarioExecutor(scenario)
    comparator = FixedComparator(ratio)
    reviewer = FixedReviewer(visual)
    validator = ProtectedBrowserValidator(
        targets=resolver,
        workflows=BrowserWorkflowRegistry((reference_app_workflow(),)),
        executor=executor,
        baselines=_baselines(),
        comparator=comparator,
        reviewer=reviewer,
    )
    return validator, store, executor, comparator, reviewer


def test_target_is_derived_from_durable_source_delivery_only() -> None:
    resolver, store = _resolver()
    target = resolver.resolve(_run(), lineage_id=LINEAGE_ID)

    assert target.project_id == PROJECT_ID
    assert target.run_id == RUN_ID
    assert target.work_specification_id == SPEC_ID
    assert target.work_specification_revision == 3
    assert target.work_specification_digest == SPEC_DIGEST
    assert target.lineage_id == LINEAGE_ID
    assert target.content_digest == CONTENT_DIGEST
    assert target.preview_deployment_id == PREVIEW_ID
    assert target.preview_origin == PREVIEW_URL
    assert target.preview_host == "parallax-preview.vercel.app"
    assert store.loads == [(RUN_ID, LINEAGE_ID)]
    assert store.persist_calls == 0


@pytest.mark.parametrize(
    ("run", "lineage_id", "delivery"),
    [
        (_run(project_id=OTHER_PROJECT_ID), LINEAGE_ID, _delivery()),
        (_run(work_specification_digest="bad"), LINEAGE_ID, _delivery()),
        (_run(work_specification_revision=0), LINEAGE_ID, _delivery()),
        (_run(), "src:" + "9" * 64, _delivery()),
        (_run(), LINEAGE_ID, _delivery(preview_status=VercelPreviewStatus.BUILDING.value)),
        (_run(), LINEAGE_ID, _delivery(preview_url="https://evil.example")),
        (_run(), LINEAGE_ID, _delivery(preview_url=None)),
    ],
)
def test_wrong_or_stale_preview_provenance_fails_closed(
    run: EngineeringRun,
    lineage_id: str,
    delivery: VerifiedDeliveryResult,
) -> None:
    resolver, _ = _resolver(delivery)
    with pytest.raises(BrowserValidationError):
        resolver.resolve(run, lineage_id=lineage_id)


def test_missing_delivery_record_fails_before_browser_execution() -> None:
    with pytest.raises(BrowserValidationError, match="SOURCE_DELIVERY"):
        BrowserTargetResolver(FakeDeliveryStore(None)).resolve(_run(), lineage_id=LINEAGE_ID)


@pytest.mark.parametrize(
    "action",
    [
        lambda: BrowserAction(BrowserActionKind.NAVIGATE, path="https://evil.example"),
        lambda: BrowserAction(BrowserActionKind.NAVIGATE, path="//evil.example"),
        lambda: BrowserAction(BrowserActionKind.NAVIGATE, path="/safe?token=secret"),
        lambda: BrowserAction(
            BrowserActionKind.FILL,
            target=SemanticTarget(SemanticTargetKind.LABEL, "Name"),
            value="authorization=secret",
        ),
        lambda: BrowserAction(BrowserActionKind.CLICK, target=None),
        lambda: BrowserAction(BrowserActionKind.SCREENSHOT, checkpoint=None),
    ],
)
def test_workflow_contract_rejects_programmable_or_secret_bearing_inputs(action) -> None:
    with pytest.raises(BrowserValidationError):
        action()


def test_unregistered_workflow_and_viewport_fail_closed() -> None:
    registry = BrowserWorkflowRegistry((reference_app_workflow(),))
    with pytest.raises(BrowserValidationError, match="not server-registered"):
        registry.resolve("caller-created-workflow", 1)

    unsafe = BrowserWorkflow(
        workflow_id="bad-viewport",
        version=1,
        viewport_ids=("unregistered-999",),
        actions=(BrowserAction(BrowserActionKind.SCREENSHOT, checkpoint="primary"),),
    )
    with pytest.raises(BrowserValidationError, match="unregistered viewport"):
        BrowserWorkflowRegistry((unsafe,))


def test_sandbox_adapter_exposes_exact_preview_host_without_generic_command_authority() -> None:
    resolver, _ = _resolver()
    target = resolver.resolve(_run(), lineage_id=LINEAGE_ID)
    workflow = reference_app_workflow()
    registry = BrowserWorkflowRegistry((workflow,))
    viewport = registry.viewport("mobile-390")
    request = BrowserExecutionRequest(target, workflow, viewport, target.preview_host)

    class Runner:
        def __init__(self) -> None:
            self.job = None

        def run(self, job):
            self.job = job
            return ScenarioExecutor().execute(request)

    runner = Runner()
    evidence = VercelSandboxBrowserExecutor(runner).execute(request)
    validate_execution_evidence(request, evidence)

    assert runner.job.exact_allowed_host == "parallax-preview.vercel.app"
    assert runner.job.preview_origin == PREVIEW_URL
    assert runner.job.network_policy == NETWORK_POLICY_EXACT_PREVIEW
    assert not hasattr(runner.job, "command")
    assert not hasattr(runner.job, "headers")
    assert not hasattr(runner.job, "cookies")
    assert not hasattr(runner.job, "environment")


@pytest.mark.parametrize(
    ("scenario", "expected_prefix"),
    [
        ("semantic", "ASSERTION:"),
        ("a11y", "ACCESSIBILITY:"),
        ("console", "CONSOLE:"),
        ("network", "NETWORK:"),
        ("external", "NETWORK:"),
        ("overflow", "LAYOUT:"),
        ("overlay", "LAYOUT:"),
    ],
)
def test_deterministic_browser_negatives_fail_before_multimodal_review(
    scenario: str,
    expected_prefix: str,
) -> None:
    validator, _, _, comparator, reviewer = _validator(scenario=scenario)
    result = validator.validate(
        _run(),
        lineage_id=LINEAGE_ID,
        workflow_id="reference-app-primary",
        workflow_version=1,
    )

    assert result.status is ProtectedValidationStatus.FAIL
    assert any(item.startswith(expected_prefix) for item in result.deterministic_defects)
    assert comparator.calls == 0
    assert reviewer.calls == 0


def test_multimodal_pass_cannot_override_deterministic_failure() -> None:
    validator, _, _, _, reviewer = _validator(scenario="overlay", visual=VisualReviewOutcome.PASS)
    result = validator.validate(
        _run(),
        lineage_id=LINEAGE_ID,
        workflow_id="reference-app-primary",
        workflow_version=1,
    )
    assert result.status is ProtectedValidationStatus.FAIL
    assert reviewer.calls == 0


def test_screenshot_regression_fails_before_multimodal_review() -> None:
    validator, _, _, comparator, reviewer = _validator(ratio=0.25)
    result = validator.validate(
        _run(),
        lineage_id=LINEAGE_ID,
        workflow_id="reference-app-primary",
        workflow_version=1,
    )
    assert result.status is ProtectedValidationStatus.FAIL
    assert result.deterministic_defects == (
        "SCREENSHOT_REGRESSION:mobile-390:primary",
        "SCREENSHOT_REGRESSION:desktop-1440:primary",
    )
    assert comparator.calls == 2
    assert reviewer.calls == 0


def test_cross_project_or_mismatched_baseline_provenance_is_rejected() -> None:
    resolver, _ = _resolver()
    target = resolver.resolve(_run(), lineage_id=LINEAGE_ID)
    workflow = reference_app_workflow()
    registry = BrowserWorkflowRegistry((workflow,))
    request = BrowserExecutionRequest(target, workflow, registry.viewport("mobile-390"), target.preview_host)
    screenshot = _screenshot(request)
    baseline = ScreenshotBaseline(
        project_id=OTHER_PROJECT_ID,
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        viewport_id=request.viewport.viewport_id,
        checkpoint="primary",
        design_state_id="wrong-project",
        artifact_ref="baseline:wrong-project",
        sha256=screenshot.sha256,
        max_difference_ratio=0.05,
    )
    difference = ScreenshotDifference(screenshot.sha256, baseline.sha256, 0.0)
    with pytest.raises(BrowserValidationError, match="different Project"):
        validate_screenshot_difference(screenshot, baseline, difference)


def test_screenshot_artifact_must_match_exact_project_run_spec_lineage_preview_workflow_and_viewport() -> None:
    resolver, _ = _resolver()
    target = resolver.resolve(_run(), lineage_id=LINEAGE_ID)
    workflow = reference_app_workflow()
    registry = BrowserWorkflowRegistry((workflow,))
    viewport = registry.viewport("mobile-390")
    request = BrowserExecutionRequest(target, workflow, viewport, target.preview_host)
    good = ScenarioExecutor().execute(request)
    validate_execution_evidence(request, good)

    wrong = replace(
        good,
        screenshots=(replace(good.screenshots[0], work_specification_digest="9" * 64),),
    )
    with pytest.raises(BrowserValidationError, match="screenshot artifact provenance"):
        validate_execution_evidence(request, wrong)


def test_off_origin_network_evidence_cannot_be_hidden_as_normal_traffic() -> None:
    resolver, _ = _resolver()
    target = resolver.resolve(_run(), lineage_id=LINEAGE_ID)
    workflow = reference_app_workflow()
    registry = BrowserWorkflowRegistry((workflow,))
    viewport = registry.viewport("mobile-390")
    request = BrowserExecutionRequest(target, workflow, viewport, target.preview_host)
    evidence = ScenarioExecutor().execute(request)
    bad_network = (NetworkFinding("GET", "evil.example", "/collect", status=204),)
    with pytest.raises(BrowserValidationError, match="unexpected external"):
        validate_execution_evidence(request, replace(evidence, network=bad_network))


def test_visual_fail_and_review_are_secondary_only_after_deterministic_pass() -> None:
    failed, _, _, _, fail_reviewer = _validator(visual=VisualReviewOutcome.FAIL)
    fail_result = failed.validate(
        _run(), lineage_id=LINEAGE_ID, workflow_id="reference-app-primary", workflow_version=1
    )
    assert fail_result.status is ProtectedValidationStatus.FAIL
    assert fail_result.deterministic_defects == ()
    assert fail_reviewer.calls == 2

    review, _, _, _, review_reviewer = _validator(visual=VisualReviewOutcome.REVIEW)
    review_result = review.validate(
        _run(), lineage_id=LINEAGE_ID, workflow_id="reference-app-primary", workflow_version=1
    )
    assert review_result.status is ProtectedValidationStatus.REVIEW
    assert review_reviewer.calls == 2


def test_structured_multimodal_findings_reject_secret_or_hidden_reasoning_material() -> None:
    with pytest.raises(BrowserValidationError, match="hidden-reasoning"):
        VisualFinding("VISUAL", "hero", "chain_of_thought: internal evaluation")
    with pytest.raises(BrowserValidationError, match="secret-bearing"):
        VisualFinding("VISUAL", "hero", "authorization=secret")


def test_pass_result_is_process_recreatable_and_does_not_republish_delivery() -> None:
    delivery = _delivery()
    store = FakeDeliveryStore(delivery.to_record())

    def build_validator() -> ProtectedBrowserValidator:
        return ProtectedBrowserValidator(
            targets=BrowserTargetResolver(store),
            workflows=BrowserWorkflowRegistry((reference_app_workflow(),)),
            executor=ScenarioExecutor(),
            baselines=_baselines(),
            comparator=FixedComparator(),
            reviewer=FixedReviewer(),
        )

    first = build_validator().validate(
        _run(), lineage_id=LINEAGE_ID, workflow_id="reference-app-primary", workflow_version=1
    )
    second = build_validator().validate(
        _run(), lineage_id=LINEAGE_ID, workflow_id="reference-app-primary", workflow_version=1
    )

    assert first.status is ProtectedValidationStatus.PASS
    assert second.status is ProtectedValidationStatus.PASS
    assert first.project_id == second.project_id == PROJECT_ID
    assert first.lineage_id == second.lineage_id == LINEAGE_ID
    assert first.preview_deployment_id == second.preview_deployment_id == PREVIEW_ID
    assert store.loads == [(RUN_ID, LINEAGE_ID), (RUN_ID, LINEAGE_ID)]
    assert store.persist_calls == 0


def test_reference_workflow_is_permanent_bounded_and_responsive() -> None:
    workflow = reference_app_workflow()
    assert workflow.workflow_id == "reference-app-primary"
    assert workflow.version == 1
    assert workflow.viewport_ids == ("mobile-390", "desktop-1440")
    assert workflow.screenshot_checkpoints == ("primary",)
    assert all(isinstance(action, BrowserAction) for action in workflow.actions)
    assert {action.kind for action in workflow.actions} >= {
        BrowserActionKind.NAVIGATE,
        BrowserActionKind.ASSERT_VISIBLE,
        BrowserActionKind.ASSERT_LAYOUT,
        BrowserActionKind.SCREENSHOT,
    }
