from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

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
    DefectPrecedence,
    DefectSeverity,
    DefectSource,
    ProtectedQualityVector,
    normalize_failure,
)
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore, InMemoryLineageMetadataStore
from parallax_api.code.live_observability import (
    EngineeringObservabilityService,
    ProtectedObservationNotFound,
)
from parallax_api.code.patching import SourcePatch
from parallax_api.code.run_events import (
    RunEventAppend,
    RunEventOutcome,
    RunEventSubsystem,
    RunEventType,
)
from parallax_api.code.service import EngineeringRunService
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.run_events import PersistentRunEventSink, RunEventRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


OWNER = "owner:wave4-release"
SOURCE_V1 = b"value = 1\n"
SOURCE_V2 = b"value = 2\n"
SOURCE_V3 = b"value = 3\n"


class StaticSourceProvider:
    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return SourcePackage(
            source_kind="repository",
            source_ref="github:acme/wave4-reference@" + "1" * 40,
            files={"app.py": SOURCE_V1},
        )


class MemoryCorrectionStateStore:
    def __init__(self) -> None:
        self.state: CorrectionSessionState | None = None

    def load(self, *, run_id: str, session_id: str):
        if self.state is None:
            return None
        return self.state if self.state.run_id == run_id and self.state.session_id == session_id else None

    def save(self, *, run, state: CorrectionSessionState, expected_revision: int):
        if self.state is None:
            if expected_revision != 0 or state.revision != 0:
                raise CorrectionStateConflict("new correction state revision mismatch")
            self.state = replace(state, revision=1)
        else:
            if self.state.revision != expected_revision or state.revision != expected_revision:
                raise CorrectionStateConflict("correction state CAS mismatch")
            self.state = replace(state, revision=expected_revision + 1)
        return self.state


class SinglePatchPlanner:
    def plan(self, context, *, lineage_id, defects):
        return CorrectionPlan(
            target_defect_ids=tuple(item.defect_id for item in defects),
            patches=(
                SourcePatch(
                    path="app.py",
                    expected_base_sha256=sha256(SOURCE_V2).hexdigest(),
                    unified_diff="--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-value = 2\n+value = 3\n",
                ),
            ),
            estimated_changed_bytes=len(SOURCE_V3),
            compute_units=1,
        )


class DurableCorrectionMutation:
    def __init__(self, store: SourceLineageStore, identity: ProjectRunIdentity, root: Path) -> None:
        self.store = store
        self.identity = identity
        self.root = root
        self.records: dict[str, CorrectionMutationResult] = {}
        self.calls = 0

    def apply(self, context, *, operation_key: str, base_lineage_id: str, plan: CorrectionPlan):
        existing = self.records.get(operation_key)
        if existing is not None:
            return replace(existing, replayed=True)
        self.calls += 1
        target = self.root / f"correction-{self.calls}"
        self.store.materialize(self.identity, base_lineage_id, target)
        try:
            source = target / "app.py"
            assert sha256(source.read_bytes()).hexdigest() == plan.patches[0].expected_base_sha256
            source.write_bytes(SOURCE_V3)
            lineage = self.store.capture_implementation(
                self.identity,
                target,
                expected_parent_lineage_id=base_lineage_id,
            )
        finally:
            shutil.rmtree(target, ignore_errors=True)
        result = CorrectionMutationResult(
            lineage_id=lineage.lineage_id,
            changed_bytes=len(SOURCE_V3),
            replayed=False,
            evidence_ref="mutation:wave4-reference-correction",
        )
        self.records[operation_key] = result
        return result


class CorrectionValidator:
    def __init__(self, *, project_id: str, run_id: str, spec_digest: str, failed_lineage: str) -> None:
        self.project_id = project_id
        self.run_id = run_id
        self.spec_digest = spec_digest
        self.failed_lineage = failed_lineage

    def validate(self, context, *, lineage_id: str):
        defects = ()
        if lineage_id == self.failed_lineage:
            defects = (
                normalize_failure(
                    source=DefectSource.TEST,
                    precedence=DefectPrecedence.DETERMINISTIC,
                    failure_code="AUTONOMOUS_TEST_FAILED",
                    severity=DefectSeverity.ERROR,
                    reproducible=True,
                    project_id=self.project_id,
                    run_id=self.run_id,
                    work_specification_digest=self.spec_digest,
                    lineage_id=lineage_id,
                    evidence_refs=("attempt:test-failed",),
                    source_path="app.py",
                ),
            )
        return CandidateValidation(
            project_id=self.project_id,
            run_id=self.run_id,
            work_specification_digest=self.spec_digest,
            lineage_id=lineage_id,
            quality=ProtectedQualityVector.from_defects(defects),
            defects=defects,
            evidence_refs=("validation:wave4-reference",),
        )


def _service(session, sink) -> EngineeringRunService:
    return EngineeringRunService(
        EngineeringRunRepository(session),
        ConversationRepository(session),
        WorkSpecificationRepository(session),
        ProjectRepository(session),
        owner_subject=OWNER,
        require_project_binding=True,
        event_sink=sink,
    )


def _execution(ids: list[str], lineage_id: str, *, acceptance_key: str, stdout: str = "ok") -> dict[str, object]:
    return {
        "protected_success": True,
        "exit_code": 0,
        "duration_ms": 1,
        "timed_out": False,
        "redacted": True,
        acceptance_key: ids,
        "source_lineage_ref": lineage_id,
        "lineage_bound_execution": True,
        "tool_id": "protected-reference-command",
        "stdout_digest": sha256(stdout.encode()).hexdigest(),
        "stdout_excerpt": stdout,
        "stderr_digest": sha256(b"").hexdigest(),
        "stderr_excerpt": "",
    }


def test_wave4_reference_release_persists_failure_correction_observation_and_review(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'wave4-release.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    object_store = InMemoryImmutableObjectStore()
    metadata_store = InMemoryLineageMetadataStore()
    lineage_store = SourceLineageStore(object_store, metadata_store)

    with Session() as session:
        events = RunEventRepository(session)
        sink = PersistentRunEventSink(events)
        projects = ProjectRepository(session)
        project = projects.create(
            owner_subject=OWNER,
            slug="wave4-reference",
            name="Wave 4 Reference",
            description="Permanent Wave 4 integrated observation reference",
            repository_ref="github:acme/wave4-reference",
        )
        conversation = ConversationRepository(session).create(
            "code",
            spec_id="P2-V0.17.5",
            project_id=project.id,
        )
        specs = WorkSpecificationRepository(session)
        draft = specs.create_draft(
            conversation_id=conversation.id,
            draft=WorkSpecificationDraft(
                title="Wave 4 integrated reference",
                objective="Prove durable failure, bounded correction, observation and REVIEW.",
                constraints=["Preserve exact Project/run/source authority."],
                acceptance_criteria=[
                    "A failed TEST remains durable and visible.",
                    "A bounded correction reaches exact-lineage REVIEW without fabricating success.",
                ],
                risks=["Observation must not become execution authority."],
                open_questions=[],
                confidence=0.99,
                program_version="wave4-reference-v1",
            ),
            model_id="wave4-reference-model",
        )
        spec = specs.approve(draft)
        service = _service(session, sink)
        run = service.activate_run(conversation_id=conversation.id, work_specification_id=spec.id)
        assert run.state == WorkflowStage.PLAN.value
        ids = sorted(item["id"] for item in service.acceptance_map_for_run(run))

        plan = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="wave4-reference:plan",
            expected_revision=run.revision,
            passed=True,
            evidence={
                "acceptance_ids_covered": ids,
                "work_items": [{"acceptance_id": item, "action": "implement"} for item in ids],
                "validation_checks": [{"acceptance_id": item, "check": "verify"} for item in ids],
            },
            program_id="wave4-reference-plan",
        )

        identity = ProjectRunIdentity(project.id, run.id)
        base = lineage_store.initialize(identity, StaticSourceProvider())
        implementation_root = tmp_path / "implementation"
        lineage_store.materialize(identity, base.lineage_id, implementation_root)
        (implementation_root / "app.py").write_bytes(SOURCE_V2)
        implemented_lineage = lineage_store.capture_implementation(
            identity,
            implementation_root,
            expected_parent_lineage_id=base.lineage_id,
        )
        shutil.rmtree(implementation_root, ignore_errors=True)
        workspace_digest = implemented_lineage.content_digest
        implementation = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.IMPLEMENT,
            operation_key="wave4-reference:implement",
            expected_revision=plan.run.revision,
            passed=True,
            evidence={
                "artifacts": [{"path": "app.py", "sha256": sha256(SOURCE_V2).hexdigest(), "size": len(SOURCE_V2)}],
                "base_revision": base.content_digest,
                "workspace_digest": workspace_digest,
                "project_ref": project.id,
                "run_id": run.id,
                "base_source_lineage_ref": base.lineage_id,
                "source_lineage_ref": implemented_lineage.lineage_id,
            },
            program_id="wave4-reference-implementation",
        )
        build = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.BUILD,
            operation_key="wave4-reference:build",
            expected_revision=implementation.run.revision,
            passed=True,
            evidence=_execution(ids, implemented_lineage.lineage_id, acceptance_key="acceptance_ids_targeted"),
            tool_id="build",
        )

        secret_excerpt = "authorization=abcdefghijklmnop"
        failed = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.TEST,
            operation_key="wave4-reference:test:failed",
            expected_revision=build.run.revision,
            passed=False,
            failure_code="AUTONOMOUS_TEST_FAILED",
            evidence={
                "protected_success": False,
                "exit_code": 1,
                "duration_ms": 1,
                "timed_out": False,
                "redacted": False,
                "acceptance_ids_verified": ids,
                "source_lineage_ref": implemented_lineage.lineage_id,
                "lineage_bound_execution": True,
                "tool_id": "test",
                "stdout_excerpt": secret_excerpt,
            },
            tool_id="test",
        )
        assert failed.run.state == WorkflowStage.FAILED.value

        context = CorrectionContext.from_run(
            failed.run,
            plan_ref="plan:P2-V0.17.5:compiled",
            dependencies=("workstream:148",),
        )
        mutation = DurableCorrectionMutation(lineage_store, identity, tmp_path)
        controller = AutonomousCorrectionController(
            run=failed.run,
            context=context,
            planner=SinglePatchPlanner(),
            mutation=mutation,
            validator=CorrectionValidator(
                project_id=project.id,
                run_id=run.id,
                spec_digest=run.work_specification_digest or "",
                failed_lineage=implemented_lineage.lineage_id,
            ),
            state_store=MemoryCorrectionStateStore(),
            budget=CorrectionBudgetPolicy(max_attempts=2),
        )
        correction = controller.run(initial_lineage_id=implemented_lineage.lineage_id)
        assert correction.status is CorrectionSessionStatus.PASSED
        assert correction.current_lineage_id != implemented_lineage.lineage_id
        assert mutation.calls == 1
        corrected_lineage = lineage_store.resolve(identity, correction.current_lineage_id)
        assert corrected_lineage.parent_lineage_id == implemented_lineage.lineage_id

        service.emit_event(
            RunEventAppend(
                project_id=project.id,
                run_id=run.id,
                event_key=f"correction:{correction.session_id}:{corrected_lineage.lineage_id}",
                event_type=RunEventType.SOURCE_LINEAGE_ACCEPTED,
                stage=WorkflowStage.TEST.value,
                outcome=RunEventOutcome.SUCCEEDED,
                subsystem=RunEventSubsystem.SOURCE_LINEAGE,
                source_lineage_ref=corrected_lineage.lineage_id,
                parent_source_lineage_ref=implemented_lineage.lineage_id,
                evidence_ref="validation:wave4-reference",
                summary="Bounded autonomous correction accepted a fresh immutable source lineage after failed TEST evidence.",
                metadata={"content_digest": corrected_lineage.content_digest},
                occurred_at=datetime.now(timezone.utc),
            )
        )

        resumed = service.resume(
            run_id=run.id,
            operation_key="wave4-reference:resume-test",
            expected_revision=failed.run.revision,
        )
        assert resumed.run.state == WorkflowStage.TEST.value
        passed_test = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.TEST,
            operation_key="wave4-reference:test:corrected",
            expected_revision=resumed.run.revision,
            passed=True,
            evidence=_execution(ids, corrected_lineage.lineage_id, acceptance_key="acceptance_ids_verified"),
            tool_id="test",
        )
        verified = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.VERIFY,
            operation_key="wave4-reference:verify",
            expected_revision=passed_test.run.revision,
            passed=True,
            evidence=_execution(ids, corrected_lineage.lineage_id, acceptance_key="acceptance_ids_verified"),
            tool_id="verify",
        )
        assert verified.run.state == WorkflowStage.REVIEW.value

        persisted = events.list_for_run(project_id=project.id, run_id=run.id, limit=200)
        assert [item.sequence for item in persisted] == list(range(1, len(persisted) + 1))
        failed_event = next(
            item for item in persisted
            if item.append.event_type is RunEventType.STAGE_RESULT
            and item.append.stage == WorkflowStage.TEST.value
            and item.append.outcome is RunEventOutcome.FAILED
        )
        corrected_event = next(
            item for item in persisted
            if item.append.event_type is RunEventType.SOURCE_LINEAGE_ACCEPTED
            and item.append.source_lineage_ref == corrected_lineage.lineage_id
        )
        passed_event = next(
            item for item in persisted
            if item.append.event_type is RunEventType.STAGE_RESULT
            and item.append.stage == WorkflowStage.TEST.value
            and item.append.outcome is RunEventOutcome.SUCCEEDED
        )
        review_event = next(item for item in persisted if item.append.event_type is RunEventType.REVIEW_REQUIRED)
        assert failed_event.sequence < corrected_event.sequence < passed_event.sequence < review_event.sequence
        assert review_event.append.outcome is RunEventOutcome.HUMAN_REQUIRED
        serialized = json.dumps([item.append.canonical_payload() for item in persisted], sort_keys=True)
        assert secret_excerpt not in serialized
        assert "authorization=" not in serialized

        observer = EngineeringObservabilityService(service, events, lineage_store=lineage_store)
        page = observer.event_page(run_id=run.id, after_sequence=failed_event.sequence - 1, limit=200)
        assert page["events"][0]["sequence"] == failed_event.sequence
        tree = observer.source_tree(run_id=run.id, lineage_id=corrected_lineage.lineage_id)
        assert tree["content_digest"] == corrected_lineage.content_digest
        source = observer.source_file(run_id=run.id, lineage_id=corrected_lineage.lineage_id, path="app.py")
        assert source["availability"] == "TEXT" and source["text"] == SOURCE_V3.decode()
        diff = observer.source_diff(
            run_id=run.id,
            from_lineage=implemented_lineage.lineage_id,
            to_lineage=corrected_lineage.lineage_id,
        )
        assert diff["changed_count"] == 1
        assert diff["files"][0]["path"] == "app.py"
        assert "-value = 2" in (diff["files"][0]["diff_text"] or "")
        assert "+value = 3" in (diff["files"][0]["diff_text"] or "")

        failed_evidence = observer.attempt_evidence(run_id=run.id, attempt_id=failed.attempt_id)
        assert failed_evidence["status"] == "FAILED"
        assert failed_evidence["failure_code"] == "AUTONOMOUS_TEST_FAILED"
        assert failed_evidence["evidence"].get("stdout_excerpt") == "[REDACTED]"
        passed_evidence = observer.attempt_evidence(run_id=run.id, attempt_id=passed_test.attempt_id)
        assert passed_evidence["status"] == "PASSED"
        assert passed_evidence["evidence"].get("source_lineage_ref") == corrected_lineage.lineage_id

        foreign_identity = ProjectRunIdentity(str(uuid4()), str(uuid4()))
        foreign = lineage_store.initialize(foreign_identity, StaticSourceProvider())
        with pytest.raises(ProtectedObservationNotFound):
            observer.source_tree(run_id=run.id, lineage_id=foreign.lineage_id)
        with pytest.raises(ProtectedObservationNotFound):
            observer.attempt_evidence(run_id=run.id, attempt_id=str(uuid4()))

        review = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.REVIEW,
            operation_key="wave4-reference:operator-review",
            expected_revision=verified.run.revision,
            passed=True,
            evidence={
                "recommendation": "PASS",
                "acceptance_ids_verified": ids,
                "workspace_digest": workspace_digest,
                "claims": ["corrected-lineage-observed", "operator-reviewed"],
                "operator_ref": "operator:wave4-release",
            },
            program_id="operator-review-wave4-reference",
        )
        assert review.run.state == WorkflowStage.COMPLETE.value


def test_wave4_run_event_migration_contract_is_additive_guarded_and_rollback_safe() -> None:
    root = Path(__file__).resolve().parents[3]
    sql = (root / "services/api/migrations/20260824_0010_run_events.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS engineering_run_events" in sql
    assert "UNIQUE (run_id, sequence)" in sql
    assert "UNIQUE (run_id, event_key)" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL ON TABLE engineering_run_events FROM anon, authenticated" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()

    app = (root / "services/api/parallax_api/main.py").read_text(encoding="utf-8")
    routes = (root / "services/api/parallax_api/routes/engineering_runs.py").read_text(encoding="utf-8")
    assert 'PARALLAX_RUN_EVENTS_ENABLED' in app
    assert 'os.getenv(_RUN_EVENTS_ENABLE_ENV) == "1"' in app
    assert 'os.getenv(_RUN_EVENTS_ENABLE_ENV) != "1"' in routes
