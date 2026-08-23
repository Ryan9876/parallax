from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionSpec
from parallax_api.code.implementation_runtime import (
    ImplementationLineageReceipt,
    ImplementationMutationError,
    ImplementationRuntimeError,
    ImplementationWorkspaceHandle,
    ProtectedImplementationRuntime,
    ProjectBindingError,
    WorkspaceLineageError,
)
from parallax_api.code.service import EngineeringRunService
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.implementation_generation import (
    GeneratedSourcePatch,
    ImplementationProposal,
)
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


PROJECT_REF = "project-11111111-1111-1111-1111-111111111111"


class ProjectBinding:
    def __init__(self, value: str = PROJECT_REF, *, fail: bool = False):
        self.value = value
        self.fail = fail

    def project_ref_for_run(self, run):
        if self.fail:
            raise ProjectBindingError("no project")
        return self.value


class LineageGateway:
    def __init__(self, workspace: Path, *, handle_project: str = PROJECT_REF, receipt_mismatch: bool = False):
        self.workspace = workspace
        self.handle_project = handle_project
        self.receipt_mismatch = receipt_mismatch
        self.accept_calls = 0

    def resolve_for_implementation(self, *, project_ref: str, run_id: str):
        return ImplementationWorkspaceHandle(
            project_ref=self.handle_project,
            run_id=run_id,
            source_lineage_ref="lineage-base",
            base_revision="source-revision-base",
            workspace_root=self.workspace,
        )

    def accept_implementation(self, *, handle, workspace_digest: str, artifacts):
        self.accept_calls += 1
        return ImplementationLineageReceipt(
            project_ref=handle.project_ref,
            run_id=handle.run_id,
            base_source_lineage_ref="wrong-base" if self.receipt_mismatch else handle.source_lineage_ref,
            source_lineage_ref="lineage-next",
            workspace_digest=workspace_digest,
        )


class FixedGenerator:
    def __init__(self, proposal: ImplementationProposal):
        self.proposal = proposal
        self.requests = []

    def generate_sync(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            proposal=self.proposal,
            model="test-model",
            program_version="test-generation-v1",
        )


class FakeExecutor:
    def __init__(self):
        self.specs: list[ExecutionSpec] = []
        self.probes: list[str] = []

    def probe(self, *, operation_key: str):
        self.probes.append(operation_key)
        return {
            "tool_id": "python",
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "PARALLAX_SANDBOX_READY",
            "stderr_excerpt": "",
            "protected_success": True,
            "executor": "test",
            "network_policy": "deny-all",
            "persistent": False,
        }

    def execute(self, spec: ExecutionSpec):
        self.specs.append(spec)
        return {
            "tool_id": spec.tool_id,
            "invocation_digest": "a" * 64,
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_digest": "b" * 64,
            "stdout_excerpt": "ok",
            "stderr_digest": "c" * 64,
            "stderr_excerpt": "",
            "timed_out": False,
            "redacted": False,
            "artifacts": [],
            "protected_success": True,
            "executor": "test",
            "network_policy": "deny-all",
            "persistent": False,
        }


def service_for(tmp_path: Path, name="runtime.db"):
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    conversations = ConversationRepository(session)
    runs = EngineeringRunRepository(session)
    work_specs = WorkSpecificationRepository(session)
    service = EngineeringRunService(runs, conversations, work_specs)
    return session, service, conversations, work_specs


def activated_run(service, conversations, work_specs):
    conversation = conversations.create("code", spec_id="P2-V0.13.0")
    draft = WorkSpecificationDraft(
        title="Implement protected source change",
        objective="Change the application value through protected implementation.",
        constraints=["Do not broaden execution authority."],
        acceptance_criteria=[
            "The application value is updated.",
            "Protected authority remains bounded.",
        ],
        risks=["Unsafe code mutation could escape the workspace."],
        open_questions=[],
        confidence=0.95,
        program_version="runtime-test",
    )
    specification = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=draft,
        model_id="test-model",
    )
    specification = work_specs.approve(specification)
    return service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=specification.id,
    )


def advance_plan(service, run):
    acceptance_ids = sorted(item["id"] for item in service.acceptance_map_for_run(run))
    result = service.complete_stage(
        run_id=run.id,
        stage=WorkflowStage.PLAN,
        operation_key=f"plan:{run.id}",
        expected_revision=run.revision,
        passed=True,
        evidence={
            "acceptance_ids_covered": acceptance_ids,
            "work_items": [{"acceptance_id": item, "action": "implement"} for item in acceptance_ids],
            "validation_checks": [{"acceptance_id": item, "check": "verify"} for item in acceptance_ids],
        },
    )
    assert result.run.state == "IMPLEMENT"
    return result.run


def source_proposal(path: str, before: str, after: str, *, acceptance_ids=None, digest=None):
    digest = digest or sha256(before.encode("utf-8")).hexdigest()
    return ImplementationProposal(
        acceptance_ids_covered=acceptance_ids or ["AC-01", "AC-02"],
        patches=[
            GeneratedSourcePatch(
                path=path,
                expected_base_sha256=digest,
                unified_diff=(
                    f"--- a/{path}\n"
                    f"+++ b/{path}\n"
                    "@@ -1 +1 @@\n"
                    f"-{before.rstrip()}\n"
                    f"+{after.rstrip()}\n"
                ),
            )
        ],
    )


def runtime_for(service, workspace: Path, proposal, *, project_binding=None, gateway=None):
    generator = FixedGenerator(proposal)
    lineage = gateway or LineageGateway(workspace)
    runtime = ProtectedImplementationRuntime(
        service,
        project_binding or ProjectBinding(),
        lineage,
        generator=generator,
    )
    return runtime, generator, lineage


def test_runtime_applies_validated_patch_verifies_lineage_and_advances_existing_protected_stage(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path)
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    target = workspace / "src" / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = advance_plan(service, activated_run(service, conversations, work_specs))
        runtime, generator, lineage = runtime_for(
            service,
            workspace,
            source_proposal("src/app.py", "value = 1\n", "value = 2\n"),
        )
        result = runtime.execute(
            run_id=run.id,
            operation_key="implement:positive",
            expected_revision=run.revision,
        )

        assert result.operation.run.state == "BUILD"
        assert result.source_lineage_ref == "lineage-next"
        assert target.read_text(encoding="utf-8") == "value = 2\n"
        assert lineage.accept_calls == 1
        assert len(generator.requests) == 1
        request = generator.requests[0]
        assert request.required_acceptance_ids == ("AC-01", "AC-02")
        assert all(str(workspace) not in json.dumps(item) for item in [request.contract_payload(), request.source_context.prompt_payload()])

        attempt = [item for item in result.operation.run.attempts if item.stage == "IMPLEMENT"][-1]
        evidence = json.loads(attempt.evidence_json)
        assert evidence["project_ref"] == PROJECT_REF
        assert evidence["base_source_lineage_ref"] == "lineage-base"
        assert evidence["source_lineage_ref"] == "lineage-next"
        assert evidence["protected_stage_authority"] is False
        assert evidence["git_mutation"] is False
        assert evidence["network_mutation"] is False
        assert evidence["deployment_mutation"] is False
        assert evidence["acceptance_ids_covered"] == ["AC-01", "AC-02"]
    finally:
        session.close()


def test_project_or_workspace_identity_mismatch_fails_before_mutation(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path, "identity.db")
    workspace = tmp_path / "identity-workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = advance_plan(service, activated_run(service, conversations, work_specs))
        gateway = LineageGateway(workspace, handle_project="project-other")
        runtime, _, _ = runtime_for(
            service,
            workspace,
            source_proposal("app.py", "value = 1\n", "value = 2\n"),
            gateway=gateway,
        )
        with pytest.raises(WorkspaceLineageError):
            runtime.execute(run_id=run.id, operation_key="implement:mismatch", expected_revision=run.revision)
        assert target.read_text(encoding="utf-8") == "value = 1\n"
        assert service.get(run.id).state == "IMPLEMENT"
        assert gateway.accept_calls == 0
    finally:
        session.close()


def test_acceptance_mismatch_fails_before_mutation_even_with_injected_generator(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path, "acceptance.db")
    workspace = tmp_path / "acceptance-workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = advance_plan(service, activated_run(service, conversations, work_specs))
        runtime, _, lineage = runtime_for(
            service,
            workspace,
            source_proposal(
                "app.py",
                "value = 1\n",
                "value = 2\n",
                acceptance_ids=["AC-02", "AC-01"],
            ),
        )
        with pytest.raises(ImplementationRuntimeError):
            runtime.execute(run_id=run.id, operation_key="implement:acceptance", expected_revision=run.revision)
        assert target.read_text(encoding="utf-8") == "value = 1\n"
        assert lineage.accept_calls == 0
        assert service.get(run.id).state == "IMPLEMENT"
    finally:
        session.close()


@pytest.mark.parametrize(
    ("path", "digest", "after"),
    [
        ("../escape.py", None, "value = 2\n"),
        ("app.py", "0" * 64, "value = 2\n"),
        ("app.py", None, "api_key = abcdefghijklmnopqrstuvwx\n"),
    ],
)
def test_wave1_safety_rejects_unsafe_stale_or_secret_proposals_without_durable_success(
    tmp_path: Path, path: str, digest: str | None, after: str
):
    session, service, conversations, work_specs = service_for(tmp_path, f"negative-{abs(hash((path, digest, after)))}.db")
    workspace = tmp_path / f"negative-{abs(hash((path, after)))}"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = advance_plan(service, activated_run(service, conversations, work_specs))
        runtime, _, lineage = runtime_for(
            service,
            workspace,
            source_proposal(path, "value = 1\n", after, digest=digest),
        )
        with pytest.raises(ImplementationMutationError):
            runtime.execute(run_id=run.id, operation_key="implement:unsafe", expected_revision=run.revision)
        assert target.read_text(encoding="utf-8") == "value = 1\n"
        assert lineage.accept_calls == 0
        assert service.get(run.id).state == "IMPLEMENT"
    finally:
        session.close()


def test_lineage_receipt_mismatch_is_distinct_post_mutation_failure_and_not_stage_success(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path, "receipt.db")
    workspace = tmp_path / "receipt-workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = advance_plan(service, activated_run(service, conversations, work_specs))
        gateway = LineageGateway(workspace, receipt_mismatch=True)
        runtime, _, _ = runtime_for(
            service,
            workspace,
            source_proposal("app.py", "value = 1\n", "value = 2\n"),
            gateway=gateway,
        )
        with pytest.raises(WorkspaceLineageError) as caught:
            runtime.execute(run_id=run.id, operation_key="implement:receipt", expected_revision=run.revision)
        assert caught.value.mutation_applied is True
        assert target.read_text(encoding="utf-8") == "value = 2\n"
        assert service.get(run.id).state == "IMPLEMENT"
        assert not [item for item in service.get(run.id).attempts if item.stage == "IMPLEMENT" and item.status == "PASSED"]
    finally:
        session.close()


def test_successful_operation_replay_does_not_mutate_twice(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path, "replay.db")
    workspace = tmp_path / "replay-workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = advance_plan(service, activated_run(service, conversations, work_specs))
        runtime, generator, lineage = runtime_for(
            service,
            workspace,
            source_proposal("app.py", "value = 1\n", "value = 2\n"),
        )
        first = runtime.execute(run_id=run.id, operation_key="implement:replay", expected_revision=run.revision)
        second = runtime.execute(run_id=run.id, operation_key="implement:replay", expected_revision=run.revision)
        assert first.operation.replayed is False
        assert second.operation.replayed is True
        assert first.operation.attempt_id == second.operation.attempt_id
        assert target.read_text(encoding="utf-8") == "value = 2\n"
        assert len(generator.requests) == 1
        assert lineage.accept_calls == 1
    finally:
        session.close()


def test_autonomy_with_explicit_runtime_advances_implement_then_build_test_verify_and_stops_at_review(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path, "autonomy-runtime.db")
    workspace = tmp_path / "autonomy-workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = activated_run(service, conversations, work_specs)
        runtime, _, _ = runtime_for(
            service,
            workspace,
            source_proposal("app.py", "value = 1\n", "value = 2\n"),
        )
        executor = FakeExecutor()
        result = AutonomyCoordinator(
            service,
            executor,
            implementation_runtime=runtime,
        ).run(
            run_id=run.id,
            operation_key="auto-implement",
            expected_revision=run.revision,
        )
        assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
        assert result.run.state == "REVIEW"
        assert [item.stage for item in result.steps] == [
            "EXECUTOR",
            "PLAN",
            "IMPLEMENT",
            "BUILD",
            "TEST",
            "VERIFY",
        ]
        assert target.read_text(encoding="utf-8") == "value = 2\n"
        assert [spec.stage for spec in executor.specs] == [WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY]
    finally:
        session.close()


def test_autonomy_runtime_failure_stops_without_fabricated_implement_success(tmp_path: Path):
    session, service, conversations, work_specs = service_for(tmp_path, "autonomy-failure.db")
    workspace = tmp_path / "autonomy-failure-workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    try:
        run = activated_run(service, conversations, work_specs)
        runtime, _, _ = runtime_for(
            service,
            workspace,
            source_proposal("app.py", "value = 1\n", "value = 2\n"),
            project_binding=ProjectBinding(fail=True),
        )
        result = AutonomyCoordinator(
            service,
            FakeExecutor(),
            implementation_runtime=runtime,
        ).run(run_id=run.id, operation_key="auto-implement-fail", expected_revision=run.revision)
        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED
        assert result.run.state == "IMPLEMENT"
        assert result.steps[-1].stage == "IMPLEMENT"
        assert result.steps[-1].outcome == "FAILED"
        assert target.read_text(encoding="utf-8") == "value = 1\n"
    finally:
        session.close()
