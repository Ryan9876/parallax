from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.agentic_runtime import AgenticRuntimeError
from parallax_api.code.agentic_runtime_live import (
    DurableAgentWorkerBridge,
    LiveAgenticControlPlane,
)
from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionSpec
from parallax_api.code.implementation_runtime import _bounded_controller_evidence
from parallax_api.code.lineage_persistence import (
    InMemoryImmutableObjectStore,
    InMemoryLineageMetadataStore,
)
from parallax_api.code.runtime_composition import EngineeringRuntimeComposition
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.worker_recovery import (
    RecoveryAction,
    StallClassification,
    WorkerLease,
    WorkerLeaseConflict,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerStallDecision,
)
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import (
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePackage,
)
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.implementation_generation import (
    GeneratedSourcePatch,
    ImplementationProposal,
)
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


class StaticSourceProvider:
    def __init__(self, files: dict[str, bytes]):
        self.files = files

    def load(self, identity: ProjectRunIdentity):
        return SourcePackage(
            source_kind="starter",
            source_ref="w6-r1-test-source",
            files=self.files,
        )


class LegacyExecutor:
    def __init__(self):
        self.execute_calls: list[ExecutionSpec] = []

    def probe(self, *, operation_key: str):
        return {
            "tool_id": "python",
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "PARALLAX_SANDBOX_READY",
            "stderr_excerpt": "",
            "protected_success": True,
            "executor": "w6-r1-test",
            "network_policy": "deny-all",
            "persistent": False,
        }

    def execute(self, spec: ExecutionSpec):
        self.execute_calls.append(spec)
        raise AssertionError("legacy executor must not run after accepted implementation lineage")


class LineageExecutor:
    def __init__(self):
        self.calls: list[tuple[WorkflowStage, str]] = []

    def execute_on_lineage(
        self,
        spec: ExecutionSpec,
        *,
        project_ref: str,
        run_id: str,
        source_lineage_ref: str,
        execution_contract,
    ):
        self.calls.append((spec.stage, source_lineage_ref))
        return {
            "tool_id": spec.tool_id,
            "exit_code": 0,
            "duration_ms": 1,
            "stdout_excerpt": "ok",
            "stderr_excerpt": "",
            "protected_success": True,
            "executor": "w6-r1-lineage-test",
            "network_policy": "deny-all",
            "persistent": False,
        }


class SelectedCandidateGenerator:
    def __init__(self, proposal: ImplementationProposal):
        self.proposal = proposal
        self.calls: list[dict[str, object]] = []

    def generate_protected(
        self,
        request,
        *,
        workspace_root,
        project_ref: str,
        run_id: str,
        base_source_lineage_ref: str,
        base_revision: str,
        proposal_validator,
        operation_key: str,
    ):
        assert proposal_validator(self.proposal) is True
        self.calls.append(
            {
                "workspace_root": workspace_root,
                "project_ref": project_ref,
                "run_id": run_id,
                "base_source_lineage_ref": base_source_lineage_ref,
                "base_revision": base_revision,
                "operation_key": operation_key,
                "source_context_digest": request.source_context.digest,
            }
        )
        generation = SimpleNamespace(
            proposal=self.proposal,
            model="w6-r1-selected-agent",
            attempts=(),
            program_version="agentic-runtime-v0.19.7:test",
        )
        evidence = {
            "runtime_version": "agentic-runtime-v0.19.7",
            "selected_candidate_id": "candidate-primary",
            "selected_proposal_digest": self.proposal.digest(),
            "source_lineage_accepted": False,
            "engineering_run_transitioned": False,
            "review_completed": False,
            "production_deployed": False,
        }
        return generation, evidence


class FakeCandidateValidator:
    pass


def create_runtime_fixture(tmp_path, name: str, acceptance: list[str]):
    engine = make_engine(f"sqlite:///{tmp_path / f'{name}.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    projects = ProjectRepository(session)
    project = projects.create(
        owner_subject="owner-a",
        slug=name,
        name=name,
        description=None,
        repository_ref=None,
    )
    conversations = ConversationRepository(session)
    work_specs = WorkSpecificationRepository(session)
    conversation = conversations.create(
        "code",
        spec_id="P2-V0.19.7",
        project_id=project.id,
    )
    draft = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=WorkSpecificationDraft(
            title="Activate the Wave 6 runtime",
            objective="Exercise the ordinary protected Engineering Run path.",
            constraints=["Preserve the existing single-writer lineage boundary."],
            acceptance_criteria=acceptance,
            risks=["Agent evidence could bypass protected runtime authority."],
            open_questions=[],
            confidence=0.99,
            program_version="w6-r1-test",
        ),
        model_id="test-model",
    )
    approved = work_specs.approve(draft)
    service = EngineeringRunService(
        EngineeringRunRepository(session),
        conversations,
        work_specs,
        projects,
        owner_subject="owner-a",
        require_project_binding=True,
    )
    run = service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=approved.id,
    )

    lineage_store = SourceLineageStore(
        InMemoryImmutableObjectStore(),
        InMemoryLineageMetadataStore(),
    )
    allocator = ProjectWorkspaceAllocator(
        tmp_path / f"{name}-allocator",
        lineage_store=lineage_store,
    )
    identity = ProjectRunIdentity(project_id=project.id, run_id=run.id)
    lease = allocator.initialize(
        identity,
        StaticSourceProvider({"app.py": b"value = 1\n"}),
    )
    base_lineage = lease.lineage
    allocator.cleanup(lease)
    return session, service, project, run, allocator, identity, base_lineage


def proposal_for_value_change(acceptance_ids: list[str]):
    return ImplementationProposal(
        acceptance_ids_covered=acceptance_ids,
        patches=[
            GeneratedSourcePatch(
                path="app.py",
                expected_base_sha256=sha256(b"value = 1\n").hexdigest(),
                unified_diff=(
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1 +1 @@\n"
                    "-value = 1\n"
                    "+value = 2\n"
                ),
            )
        ],
    )


def live_control(service, allocator):
    return LiveAgenticControlPlane(
        service,
        allocator,
        candidate_validator=FakeCandidateValidator(),
    )


def test_live_plan_uses_ordinary_plan_transition_and_smallest_adequate_team(tmp_path):
    session, service, _, run, allocator, _, _ = create_runtime_fixture(
        tmp_path,
        "single-agent",
        [
            "Update the application source safely.",
            "Preserve the existing application behavior.",
        ],
    )
    try:
        control = live_control(service, allocator)
        coordinator = AutonomyCoordinator(
            service,
            LegacyExecutor(),
            plan_runtime=control,
        )
        result = coordinator.run(
            run_id=run.id,
            operation_key="w6-r1:plan-single",
            expected_revision=run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_REQUIRED
        assert result.run.state == WorkflowStage.IMPLEMENT.value
        plan_attempt = next(
            item for item in result.run.attempts
            if item.stage == WorkflowStage.PLAN.value and item.status == "PASSED"
        )
        evidence = json.loads(plan_attempt.evidence_json)
        assert plan_attempt.program_id == control.program_id
        assert evidence["decision_kind"] == "SERVER_OWNED_AGENTIC_PLAN"
        assert evidence["selected_agent_count"] == 1
        assert evidence["canonical_source_writer_count"] == 1
        assert evidence["operator_selected_agents"] is False
        assert evidence["work_items"]
        assert evidence["validation_checks"]
        assert evidence["acceptance_ids_covered"] == ["AC-01", "AC-02"]
        assert control.competition_policy.minimum_expected_quality_gain == 1.0
    finally:
        session.close()


def test_live_plan_uses_one_coherent_source_unit_for_multi_domain_acceptance(tmp_path):
    session, service, _, run, allocator, _, _ = create_runtime_fixture(
        tmp_path,
        "coherent-implementation",
        [
            "Update the client button layout.",
            "Update the server API endpoint.",
        ],
    )
    try:
        control = live_control(service, allocator)
        evidence = control.plan(run=run, operation_key="p2329:plan-coherent")

        assert evidence["selected_agent_count"] == 1
        units = evidence["work_units"]
        assert len(units) == 1
        assert units[0]["unit_id"] == "implementation"
        assert units[0]["acceptance_ids"] == ["AC-01", "AC-02"]
        assert units[0]["coordination_domains"] == ["source"]
        assert evidence["operator_selected_agents"] is False
        assert control.competition_policy.minimum_expected_quality_gain == 1.0
    finally:
        session.close()

def test_selected_candidate_still_uses_existing_safe_mutation_lineage_and_later_stages(tmp_path):
    session, service, project, run, allocator, identity, base = create_runtime_fixture(
        tmp_path,
        "selected-candidate",
        [
            "Change the protected application value.",
            "Preserve the protected application source contract.",
        ],
    )
    try:
        legacy = LegacyExecutor()
        lineage_executor = LineageExecutor()
        runtime = EngineeringRuntimeComposition(
            service,
            allocator,
            legacy,
            lineage_executor=lineage_executor,
        )
        runtime.coordinator.plan_runtime = live_control(service, allocator)
        selected = SelectedCandidateGenerator(
            proposal_for_value_change(["AC-01", "AC-02"])
        )
        runtime.implementation_runtime.generator = selected

        result = runtime.run(
            run_id=run.id,
            operation_key="w6-r1:selected-candidate",
            expected_revision=run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED
        assert result.run.state == WorkflowStage.REVIEW.value
        assert len(selected.calls) == 1
        call = selected.calls[0]
        assert call["project_ref"] == project.id
        assert call["run_id"] == run.id
        assert call["base_source_lineage_ref"] == base.lineage_id

        accepted = allocator.current_lineage(identity)
        assert accepted.parent_lineage_id == base.lineage_id
        assert accepted.lineage_id != base.lineage_id
        assert legacy.execute_calls == []
        assert [item[0] for item in lineage_executor.calls] == [
            WorkflowStage.BUILD,
            WorkflowStage.TEST,
            WorkflowStage.VERIFY,
        ]
        assert all(item[1] == accepted.lineage_id for item in lineage_executor.calls)

        implement = next(
            item for item in result.run.attempts
            if item.stage == WorkflowStage.IMPLEMENT.value and item.status == "PASSED"
        )
        evidence = json.loads(implement.evidence_json)
        assert evidence["source_lineage_ref"] == accepted.lineage_id
        assert evidence["controller_evidence"]["selected_candidate_id"] == "candidate-primary"
        assert evidence["controller_evidence"]["source_lineage_accepted"] is False
        assert evidence["controller_evidence"]["engineering_run_transitioned"] is False
    finally:
        session.close()


def test_controller_evidence_cannot_claim_authority_or_persist_sensitive_fields():
    with pytest.raises(ValueError):
        _bounded_controller_evidence(
            {
                "production_deployed": True,
                "source_lineage_accepted": False,
            }
        )
    with pytest.raises(ValueError):
        _bounded_controller_evidence(
            {
                "provider_token": "must-not-persist",
                "production_deployed": False,
            }
        )


class ExpiredRecovery:
    def __init__(self):
        self.calls: list[str] = []

    def acquire(self, *, run_id: str):
        self.calls.append("acquire")
        raise WorkerLeaseExpired("expired")

    def classify_and_stall(self, *, run_id: str, evidence, blocker_code: str):
        self.calls.append("classify")
        assert evidence.process_lost is True
        assert blocker_code == "AGENTIC_PROCESS_LOSS"
        return WorkerStallDecision(
            StallClassification.PROCESS_LOSS,
            RecoveryAction.REASSIGN,
            False,
        )

    def begin_recovery(self, *, run_id: str):
        self.calls.append("begin")
        return SimpleNamespace()

    def reassign(self, *, run_id: str):
        self.calls.append("reassign")
        return WorkerLease(
            execution_id="worker-execution",
            run_id=run_id,
            owner_id="worker:new-owner",
            generation=2,
            expires_at=datetime.now(timezone.utc),
        )


def test_process_loss_recovery_requires_accepted_reassignment_generation():
    recovery = ExpiredRecovery()
    bridge = DurableAgentWorkerBridge(
        SimpleNamespace(),
        recovery=recovery,
    )

    lease = bridge.acquire(run_id="run-1")

    assert lease.generation == 2
    assert recovery.calls == ["acquire", "classify", "begin", "reassign"]


class CompetingRecovery:
    def acquire(self, *, run_id: str):
        raise WorkerLeaseConflict("active")

    def health(self, *, run_id: str):
        return SimpleNamespace(
            state=WorkerLifecycleState.RUNNING,
            next_recovery_action=None,
            human_required=False,
        )


def test_active_competing_worker_fails_closed_instead_of_being_taken_over():
    bridge = DurableAgentWorkerBridge(
        SimpleNamespace(),
        recovery=CompetingRecovery(),
    )

    with pytest.raises(AgenticRuntimeError):
        bridge.acquire(run_id="run-1")



class _DispatchCheckpointReached(RuntimeError):
    pass


class _DispatchCheckpointProbe:
    def __init__(self):
        self.steps: list[tuple[str, str, tuple[str, ...]]] = []
        self.stopped = False

    def acquire(self, *, run_id: str):
        return WorkerLease(
            execution_id="dispatch-probe",
            run_id=run_id,
            owner_id="worker:dispatch-probe",
            generation=1,
            expires_at=datetime.now(timezone.utc),
        )

    def checkpoint(
        self,
        lease,
        *,
        plan,
        work_unit_id: str,
        source_lineage_ref: str,
        step: str,
        evidence_refs: tuple[str, ...],
        state=WorkerLifecycleState.CHECKPOINTED,
    ):
        self.steps.append((step, source_lineage_ref, evidence_refs))
        if step == "AGENT_DISPATCH":
            raise _DispatchCheckpointReached("dispatch checkpoint reached")
        return lease

    def stop_bounded(self, *, run_id: str) -> None:
        self.stopped = True


def test_live_agent_task_binds_real_source_context_digest_before_dispatch(tmp_path):
    from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
    from parallax_api.intelligence.implementation_generation import (
        AcceptanceRequirement,
        ImplementationGenerationRequest,
    )

    session, service, _, run, allocator, _, base = create_runtime_fixture(
        tmp_path,
        "live-source-context-digest",
        [
            "Create the one approved proof file.",
            "Preserve all existing source bytes.",
        ],
    )
    try:
        control = live_control(service, allocator)
        coordinator = AutonomyCoordinator(
            service,
            LegacyExecutor(),
            plan_runtime=control,
        )
        planned = coordinator.run(
            run_id=run.id,
            operation_key="w6-r1:source-context-plan",
            expected_revision=run.revision,
        )
        assert planned.run.state == WorkflowStage.IMPLEMENT.value

        current = service.get(run.id)
        plan = control._verify_plan_evidence(
            run=current,
            base_source_lineage_ref=base.lineage_id,
            source_content_digest=base.content_digest,
        )
        context_digest = sha256(b"bounded-live-source-context").hexdigest()
        source = SourceContextSnapshot(
            files=(
                SourceContextFile(
                    path="app.py",
                    sha256=sha256(b"value = 1\n").hexdigest(),
                    size=len(b"value = 1\n"),
                    content="value = 1\n",
                ),
            ),
            digest=context_digest,
            total_bytes=len(b"value = 1\n"),
            excluded_secret_files=0,
            omitted_bounded_files=0,
        )
        acceptance = tuple(
            AcceptanceRequirement(id=str(item["id"]), text=str(item["text"]))
            for item in service.acceptance_map_for_run(current)
        )
        request = ImplementationGenerationRequest(
            work_specification_id=current.work_specification_id or "",
            work_specification_revision=int(current.work_specification_revision or 0),
            work_specification_digest=current.work_specification_digest or "",
            title="Bound live source-context identity",
            objective="Reach the durable S1 dispatch checkpoint without changing authority.",
            constraints=("Preserve exact source authority.",),
            acceptance=acceptance,
            source_context=source,
        )

        probe = _DispatchCheckpointProbe()
        control.worker_bridge = probe
        with pytest.raises(_DispatchCheckpointReached):
            control._proposal_for_plan(
                plan,
                request,
                proposal_validator=lambda proposal: True,
                alternative_round=1,
            )

        assert probe.stopped is True
        assert len(probe.steps) == 1
        step, lineage_ref, evidence_refs = probe.steps[0]
        assert step == "AGENT_DISPATCH"
        assert lineage_ref == base.lineage_id
        assert any(item.startswith("task:") for item in evidence_refs)
        assert context_digest != base.content_digest
    finally:
        session.close()


def test_hosted_runtime_admits_canonical_model_priority_independent_of_adapter_input_order():
    from parallax_api.code.agentic_runtime import AgenticControlPlane, HostedImplementationAgent, _MODEL_ORDER

    control = object.__new__(AgenticControlPlane)
    control.adapters = tuple(HostedImplementationAgent(model) for model in reversed(_MODEL_ORDER))
    roster = control._roster
    model_by_digest = {
        HostedImplementationAgent(model).describe().digest: model
        for model in _MODEL_ORDER
    }
    assert tuple(model_by_digest[item.identity_digest] for item in roster.entries) == _MODEL_ORDER
    assert tuple(item.selection_priority for item in roster.entries) == (0, 1, 2)
