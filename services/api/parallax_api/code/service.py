from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from ..models import Conversation, EngineeringRun, WorkSpecification
from ..intelligence.repository_identity import find_repository_identity_conflict
from ..projects.repository import ProjectRepository
from ..repositories.conversations import ConversationRepository
from ..repositories.engineering_runs import EngineeringRunRepository, RecordedMutation
from ..repositories.work_specifications import WorkSpecificationRepository
from .domain import ACTIVE_STAGES, TERMINAL_STAGES, AttemptStatus, WorkflowStage
from .run_events import (
    RunEventAppend,
    RunEventOutcome,
    RunEventSink,
    RunEventSubsystem,
    RunEventType,
)
from .state_machine import ProtectedRunPolicy, RevisionConflict, RunTransitionError, SpecBindingError
from .protected import (
    ProtectedEvidenceError,
    STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE,
    validate_execution,
    validate_implementation,
    validate_plan,
    validate_review,
    validate_specification_binding,
    validate_structural_execution,
)
from .validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    ExecutionContractIdentity,
    ValidationProfileError,
)
from .work_spec_binding import acceptance_map, required_acceptance_ids, work_specification_digest


class EngineeringRunNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class RunOperationResult:
    run: EngineeringRun
    attempt_id: str
    replayed: bool


@dataclass(frozen=True, slots=True)
class ReviewReworkContext:
    digest: str
    acceptance_ids: tuple[str, ...]
    finding: str
    base_source_lineage_ref: str
    workspace_digest: str


class EngineeringRunService:
    def __init__(
        self,
        run_repository: EngineeringRunRepository,
        conversation_repository: ConversationRepository,
        work_specification_repository: WorkSpecificationRepository | None = None,
        project_repository: ProjectRepository | None = None,
        *,
        owner_subject: str | None = None,
        require_project_binding: bool = False,
        policy: ProtectedRunPolicy | None = None,
        event_sink: RunEventSink | None = None,
    ):
        self.runs = run_repository
        self.conversations = conversation_repository
        self.work_specifications = work_specification_repository or WorkSpecificationRepository(run_repository.session)
        self.projects = project_repository
        self.owner_subject = owner_subject.strip() if owner_subject else None
        self.require_project_binding = require_project_binding
        self.policy = policy or ProtectedRunPolicy()
        self.event_sink = event_sink

    @staticmethod
    def _event_time(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _operation_ref(operation_key: str) -> str:
        return "op:" + sha256(operation_key.encode("utf-8")).hexdigest()

    def emit_event(self, event: RunEventAppend) -> None:
        """Persist one non-authoritative observation when Wave 4 is configured."""

        if self.event_sink is not None:
            self.event_sink.emit(event)

    def _emit_run_created(self, run: EngineeringRun) -> None:
        if self.event_sink is None or not run.project_id:
            return
        self.emit_event(
            RunEventAppend(
                project_id=run.project_id,
                run_id=run.id,
                event_key=f"run:{run.id}:created",
                event_type=RunEventType.RUN_CREATED,
                stage=WorkflowStage.SPECIFY.value,
                outcome=RunEventOutcome.INFO,
                subsystem=RunEventSubsystem.RUN,
                summary="Engineering Run created with canonical Project and approved Work Specification binding.",
                metadata={"current_state": WorkflowStage.SPECIFY.value, "run_revision": 0},
                occurred_at=self._event_time(run.created_at),
            )
        )

    @staticmethod
    def _attempt_subsystem(stage: str) -> RunEventSubsystem:
        if stage == WorkflowStage.IMPLEMENT.value:
            return RunEventSubsystem.IMPLEMENTATION
        if stage in {
            WorkflowStage.BUILD.value,
            WorkflowStage.TEST.value,
            WorkflowStage.VERIFY.value,
        }:
            return RunEventSubsystem.EXECUTION
        if stage == WorkflowStage.REVIEW.value:
            return RunEventSubsystem.REVIEW
        return RunEventSubsystem.RUN

    @staticmethod
    def _attempt_metadata(mutation: RecordedMutation) -> dict[str, object]:
        attempt = mutation.attempt
        metadata: dict[str, object] = {"attempt_number": int(attempt.attempt_number)}
        if attempt.program_id:
            metadata["program_id"] = attempt.program_id
        if attempt.tool_id:
            metadata["tool_id"] = attempt.tool_id
        try:
            evidence = json.loads(attempt.evidence_json or "{}")
        except json.JSONDecodeError:
            evidence = {}
        if not isinstance(evidence, dict):
            evidence = {}
        for key in ("workspace_digest", "content_digest"):
            value = evidence.get(key)
            if isinstance(value, str) and len(value) == 64:
                metadata[key] = value
        for key in ("lineage_bound_execution", "timed_out", "redacted", "mutation_applied", "plan_refresh_authorized"):
            value = evidence.get(key)
            if isinstance(value, bool):
                metadata[key] = value
        error_class = evidence.get("error_class")
        if isinstance(error_class, str) and len(error_class) <= 80 and error_class.isidentifier():
            metadata["error_class"] = error_class
        value = evidence.get("exit_code")
        if isinstance(value, int):
            metadata["exit_code"] = value
        artifacts = evidence.get("artifacts")
        if isinstance(artifacts, list):
            metadata["artifact_count"] = len(artifacts)
        for acceptance_key in (
            "acceptance_ids",
            "acceptance_ids_covered",
            "acceptance_ids_targeted",
            "acceptance_ids_verified",
        ):
            ids = evidence.get(acceptance_key)
            if isinstance(ids, list):
                metadata["acceptance_count"] = len(ids)
                break
        return metadata

    @staticmethod
    def _attempt_lineage(mutation: RecordedMutation, key: str) -> str | None:
        try:
            evidence = json.loads(mutation.attempt.evidence_json or "{}")
        except json.JSONDecodeError:
            return None
        if not isinstance(evidence, dict):
            return None
        value = evidence.get(key)
        return value if isinstance(value, str) and value.startswith("src:") else None

    def _emit_attempt_result(self, mutation: RecordedMutation) -> None:
        if self.event_sink is None or not mutation.run.project_id:
            return
        attempt = mutation.attempt
        status = attempt.status
        control = status in {
            AttemptStatus.PAUSED.value,
            AttemptStatus.RESUMED.value,
            AttemptStatus.CANCELLED.value,
            AttemptStatus.SPEC_AMENDMENT.value,
        }
        if status == AttemptStatus.PASSED.value:
            outcome = RunEventOutcome.SUCCEEDED
        elif status == AttemptStatus.FAILED.value:
            outcome = RunEventOutcome.FAILED
        elif status == AttemptStatus.SPEC_AMENDMENT.value:
            outcome = RunEventOutcome.HUMAN_REQUIRED
        elif status in {AttemptStatus.PAUSED.value, AttemptStatus.RESUMED.value}:
            outcome = RunEventOutcome.PROGRESSED
        else:
            outcome = RunEventOutcome.INFO

        metadata = self._attempt_metadata(mutation)
        if control:
            metadata["control_status"] = status
        self.emit_event(
            RunEventAppend(
                project_id=mutation.run.project_id,
                run_id=mutation.run.id,
                event_key=f"attempt:{attempt.id}:result",
                event_type=RunEventType.RUN_CONTROL if control else RunEventType.STAGE_RESULT,
                stage=attempt.stage,
                outcome=outcome,
                subsystem=self._attempt_subsystem(attempt.stage),
                attempt_id=attempt.id,
                source_lineage_ref=self._attempt_lineage(mutation, "source_lineage_ref"),
                operation_ref=self._operation_ref(attempt.operation_key),
                evidence_ref=f"attempt:{attempt.id}",
                failure_code=attempt.failure_code,
                summary=(
                    f"Engineering Run control recorded as {status}."
                    if control
                    else f"Protected {attempt.stage} attempt recorded as {status}."
                ),
                metadata=metadata,
                occurred_at=self._event_time(attempt.completed_at),
            )
        )

        if attempt.stage == WorkflowStage.IMPLEMENT.value and status == AttemptStatus.PASSED.value:
            lineage = self._attempt_lineage(mutation, "source_lineage_ref")
            parent = self._attempt_lineage(mutation, "base_source_lineage_ref")
            if lineage is not None:
                lineage_metadata = {
                    key: value
                    for key, value in metadata.items()
                    if key in {"workspace_digest", "artifact_count", "program_id", "tool_id"}
                }
                self.emit_event(
                    RunEventAppend(
                        project_id=mutation.run.project_id,
                        run_id=mutation.run.id,
                        event_key=f"lineage:{attempt.id}",
                        event_type=RunEventType.SOURCE_LINEAGE_ACCEPTED,
                        stage=WorkflowStage.IMPLEMENT.value,
                        outcome=RunEventOutcome.SUCCEEDED,
                        subsystem=RunEventSubsystem.SOURCE_LINEAGE,
                        attempt_id=attempt.id,
                        source_lineage_ref=lineage,
                        parent_source_lineage_ref=parent,
                        evidence_ref=f"attempt:{attempt.id}",
                        summary="Protected implementation accepted a new immutable source lineage.",
                        metadata=lineage_metadata,
                        occurred_at=self._event_time(attempt.completed_at),
                    )
                )

    def _emit_replay(self, mutation: RecordedMutation) -> None:
        if self.event_sink is None or not mutation.run.project_id or not mutation.replayed:
            return
        attempt = mutation.attempt
        self.emit_event(
            RunEventAppend(
                project_id=mutation.run.project_id,
                run_id=mutation.run.id,
                event_key=f"attempt:{attempt.id}:replay",
                event_type=RunEventType.OPERATION_REPLAY,
                stage=attempt.stage,
                outcome=RunEventOutcome.REPLAYED,
                subsystem=self._attempt_subsystem(attempt.stage),
                attempt_id=attempt.id,
                operation_ref=self._operation_ref(attempt.operation_key),
                evidence_ref=f"attempt:{attempt.id}",
                summary="Idempotent operation retry resolved the existing authoritative attempt without a new mutation.",
                metadata={"attempt_number": int(attempt.attempt_number)},
                occurred_at=self._event_time(attempt.completed_at),
            )
        )

    def _emit_review_required(self, run: EngineeringRun, attempt_id: str) -> None:
        if self.event_sink is None or not run.project_id or run.state != WorkflowStage.REVIEW.value:
            return
        self.emit_event(
            RunEventAppend(
                project_id=run.project_id,
                run_id=run.id,
                event_key=f"run:{run.id}:review:{run.revision}",
                event_type=RunEventType.REVIEW_REQUIRED,
                stage=WorkflowStage.REVIEW.value,
                outcome=RunEventOutcome.HUMAN_REQUIRED,
                subsystem=RunEventSubsystem.REVIEW,
                attempt_id=attempt_id,
                evidence_ref=f"attempt:{attempt_id}",
                summary="Protected autonomous execution reached the explicit operator REVIEW boundary.",
                metadata={"current_state": WorkflowStage.REVIEW.value, "run_revision": int(run.revision)},
                occurred_at=self._event_time(run.updated_at),
            )
        )

    def _conversation_for_access(self, conversation_id: str) -> Conversation | None:
        if self.owner_subject:
            return self.conversations.get_for_owner(conversation_id, self.owner_subject)
        return self.conversations.get(conversation_id)

    def _code_conversation(
        self,
        conversation_id: str,
        spec_id: str | None = None,
        *,
        require_project: bool = False,
    ) -> Conversation:
        conversation = self._conversation_for_access(conversation_id)
        if conversation is None:
            raise EngineeringRunNotFound("conversation not found")
        if conversation.mode != "code":
            raise SpecBindingError("engineering runs require a Code conversation")
        if conversation.status == "SPEC_AMENDMENT":
            raise SpecBindingError("conversation requires a specification amendment before Code execution")
        if spec_id is not None and conversation.spec_id != spec_id:
            raise SpecBindingError(
                f"run spec {spec_id} does not match durable conversation spec {conversation.spec_id}"
            )
        if require_project and conversation.project_id is None:
            raise SpecBindingError("new engineering runs require a Project-bound Code conversation")
        return conversation

    def _assert_run_access(self, run: EngineeringRun) -> None:
        if not self.owner_subject or run.project_id is None:
            return
        if self.projects is None or self.projects.get_for_owner(run.project_id, self.owner_subject) is None:
            raise EngineeringRunNotFound("engineering run not found")

    def _assert_run_project_binding(self, run: EngineeringRun, *, require_project: bool) -> Conversation:
        conversation = self._conversation_for_access(run.conversation_id)
        if conversation is None:
            raise EngineeringRunNotFound("conversation not found")
        if run.project_id != conversation.project_id:
            raise SpecBindingError("engineering run Project identity does not match its conversation")
        if require_project and run.project_id is None:
            raise SpecBindingError("historical unbound engineering runs cannot enter protected execution")
        return conversation

    @staticmethod
    def _repository_target_texts(conversation: Conversation, specification: WorkSpecification) -> tuple[str, ...]:
        latest_user = next(
            (
                item.content.strip()
                for item in reversed(conversation.messages)
                if item.role == "user" and item.content.strip()
            ),
            "",
        )
        return tuple(
            value
            for value in (latest_user, specification.title, specification.objective)
            if isinstance(value, str) and value.strip()
        )

    def _assert_repository_identity_compatible(
        self,
        *,
        conversation_id: str,
        specification: WorkSpecification,
    ) -> None:
        conversation = self._conversation_for_access(conversation_id)
        if conversation is None:
            raise EngineeringRunNotFound("conversation not found")
        if conversation.mode != "code" or conversation.project_id is None:
            return
        if self.projects is None or not self.owner_subject:
            if self.require_project_binding:
                raise SpecBindingError("Project repository binding service unavailable")
            return
        project = self.projects.get_for_owner(conversation.project_id, self.owner_subject)
        if project is None:
            raise EngineeringRunNotFound("Project not found")
        if not project.repository_ref:
            return
        conflict = find_repository_identity_conflict(
            canonical_repository_ref=project.repository_ref,
            target_texts=self._repository_target_texts(conversation, specification),
        )
        if conflict is not None:
            raise SpecBindingError(conflict.public_message)

    def _approved_work_specification(
        self,
        *,
        conversation_id: str,
        work_specification_id: str | None,
    ) -> WorkSpecification:
        specification = (
            self.work_specifications.get(work_specification_id)
            if work_specification_id
            else self.work_specifications.latest_approved(conversation_id)
        )
        if specification is None:
            raise SpecBindingError("operator-approved work specification required before Code execution")
        if specification.conversation_id != conversation_id:
            raise SpecBindingError("work specification belongs to a different conversation")
        if specification.status != "APPROVED":
            raise SpecBindingError("work specification must be explicitly approved before Code execution")
        if specification.revision < 1:
            raise SpecBindingError("work specification revision is invalid")
        self._assert_repository_identity_compatible(
            conversation_id=conversation_id,
            specification=specification,
        )
        return specification

    def _bound_work_specification(
        self,
        run: EngineeringRun,
        *,
        require_project: bool = False,
    ) -> WorkSpecification:
        self._assert_run_access(run)
        self._assert_run_project_binding(run, require_project=require_project)
        if (
            not run.work_specification_id
            or run.work_specification_revision is None
            or not run.work_specification_digest
        ):
            raise SpecBindingError("historical engineering run has no approved work specification binding")
        specification = self.work_specifications.get(run.work_specification_id)
        if specification is None:
            raise SpecBindingError("bound work specification no longer exists")
        if specification.conversation_id != run.conversation_id:
            raise SpecBindingError("bound work specification conversation mismatch")
        if specification.revision != run.work_specification_revision:
            raise SpecBindingError("bound work specification revision mismatch")
        if specification.status not in {"APPROVED", "SUPERSEDED"}:
            raise SpecBindingError("bound work specification is not an approved execution contract")
        if work_specification_digest(specification) != run.work_specification_digest:
            raise SpecBindingError("bound work specification content changed after execution binding")
        return specification

    def create_run(
        self,
        *,
        conversation_id: str,
        spec_id: str,
        work_specification_id: str,
        workspace_ref: str | None = None,
    ) -> EngineeringRun:
        if self.require_project_binding and workspace_ref is not None:
            raise SpecBindingError("caller-supplied workspace_ref is not execution authority")
        conversation = self._code_conversation(
            conversation_id,
            spec_id,
            require_project=self.require_project_binding,
        )
        specification = self._approved_work_specification(
            conversation_id=conversation.id,
            work_specification_id=work_specification_id,
        )
        run = self.runs.create(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
            project_id=conversation.project_id,
            work_specification_id=specification.id,
            work_specification_revision=specification.revision,
            work_specification_digest=work_specification_digest(specification),
            workspace_ref=None if self.require_project_binding else workspace_ref,
        )
        self._emit_run_created(run)
        return run

    def activate_run(
        self,
        *,
        conversation_id: str,
        work_specification_id: str | None = None,
        workspace_ref: str | None = None,
    ) -> EngineeringRun:
        if self.require_project_binding and workspace_ref is not None:
            raise SpecBindingError("caller-supplied workspace_ref is not execution authority")
        conversation = self._code_conversation(
            conversation_id,
            require_project=self.require_project_binding,
        )
        specification = self._approved_work_specification(
            conversation_id=conversation.id,
            work_specification_id=work_specification_id,
        )
        digest = work_specification_digest(specification)
        run = self.runs.latest_for_binding(conversation.id, specification.id)

        if run is not None and WorkflowStage(run.state) not in TERMINAL_STAGES:
            self._assert_run_access(run)
            if self.require_project_binding and run.project_id != conversation.project_id:
                raise SpecBindingError("existing engineering run Project binding does not match the conversation")
            if run.work_specification_revision != specification.revision or run.work_specification_digest != digest:
                raise SpecBindingError("existing engineering run binding does not match the approved specification")
            if not self.require_project_binding and workspace_ref is not None and run.workspace_ref != workspace_ref:
                raise SpecBindingError("existing engineering run workspace binding cannot be changed")
        else:
            run = self.runs.create(
                conversation_id=conversation.id,
                spec_id=conversation.spec_id,
                project_id=conversation.project_id,
                work_specification_id=specification.id,
                work_specification_revision=specification.revision,
                work_specification_digest=digest,
                workspace_ref=None if self.require_project_binding else workspace_ref,
            )

        self._emit_run_created(run)
        if run.state != WorkflowStage.SPECIFY.value:
            return run

        required = required_acceptance_ids(specification)
        activated = self.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.SPECIFY,
            operation_key=f"bind:{run.id}:{digest}",
            expected_revision=run.revision,
            passed=True,
            evidence={
                "work_specification_id": specification.id,
                "work_specification_revision": specification.revision,
                "work_specification_digest": digest,
                "acceptance_ids": sorted(required),
            },
            program_id="protected-spec-binding-v0.8.0",
        )
        return activated.run

    def latest_for_conversation(self, conversation_id: str) -> EngineeringRun | None:
        conversation = self._code_conversation(conversation_id, require_project=False)
        run = self.runs.latest_for_conversation(conversation.id)
        if run is not None:
            self._assert_run_access(run)
        return run

    def acceptance_map_for_run(self, run: EngineeringRun) -> list[dict[str, str]]:
        if not run.work_specification_id:
            return []
        return acceptance_map(self._bound_work_specification(run, require_project=False))

    def get(self, run_id: str) -> EngineeringRun:
        run = self.runs.get(run_id)
        if run is None:
            raise EngineeringRunNotFound("engineering run not found")
        self._assert_run_access(run)
        return run

    def _idempotent_replay(self, run: EngineeringRun, operation_key: str) -> RunOperationResult | None:
        existing = self.runs.find_operation(run.id, operation_key)
        if existing is None:
            return None
        return self._result(
            RecordedMutation(run=self.get(run.id), attempt=existing, replayed=True)
        )

    @staticmethod
    def _require_revision(run: EngineeringRun, expected_revision: int) -> None:
        if run.revision != expected_revision:
            raise RevisionConflict(
                f"stale engineering run revision: expected {expected_revision}, current {run.revision}"
            )


    @staticmethod
    def _normalize_review_rework_finding(value: str) -> str:
        if not isinstance(value, str):
            raise RunTransitionError("REVIEW rework finding must be text")
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized or len(normalized) > 1200:
            raise RunTransitionError("REVIEW rework finding must contain 1 to 1200 characters")
        if any(ord(ch) < 32 and ch not in {"\n", "\t"} for ch in normalized):
            raise RunTransitionError("REVIEW rework finding contains unsupported control characters")
        return normalized

    @staticmethod
    def _review_rework_digest(acceptance_ids: tuple[str, ...], finding: str) -> str:
        payload = {
            "version": "review-rework-v1",
            "acceptance_ids": list(acceptance_ids),
            "finding": finding,
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _valid_lineage_ref(value: object) -> bool:
        return (
            isinstance(value, str)
            and value.startswith("src:")
            and len(value) == 68
            and all(ch in "0123456789abcdef" for ch in value[4:])
        )

    @staticmethod
    def _valid_digest(value: object) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)

    def _latest_reviewed_implementation(self, run: EngineeringRun) -> tuple[str, str]:
        for attempt in reversed(run.attempts):
            if attempt.stage != WorkflowStage.IMPLEMENT.value or attempt.status != AttemptStatus.PASSED.value:
                continue
            try:
                evidence = json.loads(attempt.evidence_json or "{}")
            except (TypeError, json.JSONDecodeError) as exc:
                raise RunTransitionError("latest reviewed IMPLEMENT evidence is malformed") from exc
            if not isinstance(evidence, dict):
                raise RunTransitionError("latest reviewed IMPLEMENT evidence is malformed")
            if evidence.get("project_ref") != run.project_id or evidence.get("run_id") != run.id:
                raise RunTransitionError("latest reviewed IMPLEMENT evidence drifted from Project/run identity")
            lineage = evidence.get("source_lineage_ref")
            workspace_digest = evidence.get("workspace_digest")
            if not self._valid_lineage_ref(lineage) or not self._valid_digest(workspace_digest):
                raise RunTransitionError("latest reviewed IMPLEMENT evidence lacks accepted source identity")
            return str(lineage), str(workspace_digest)
        raise RunTransitionError("REVIEW rework requires durable accepted IMPLEMENT evidence")

    def _context_from_rework_attempt(self, attempt) -> ReviewReworkContext:
        try:
            evidence = json.loads(attempt.evidence_json or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise RunTransitionError("durable REVIEW rework evidence is malformed") from exc
        if not isinstance(evidence, dict) or evidence.get("review_rework_version") != "review-rework-v1":
            raise RunTransitionError("durable REVIEW rework evidence is malformed")
        raw_ids = evidence.get("acceptance_ids_rework")
        finding = evidence.get("finding")
        if not isinstance(raw_ids, list) or not raw_ids or not all(isinstance(item, str) for item in raw_ids):
            raise RunTransitionError("durable REVIEW rework acceptance identity is malformed")
        ids = tuple(raw_ids)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise RunTransitionError("durable REVIEW rework acceptance identity is not canonical")
        normalized = self._normalize_review_rework_finding(finding)
        digest = evidence.get("review_rework_context_digest")
        if digest != self._review_rework_digest(ids, normalized):
            raise RunTransitionError("durable REVIEW rework context digest mismatch")
        lineage = evidence.get("base_source_lineage_ref")
        workspace_digest = evidence.get("workspace_digest")
        if not self._valid_lineage_ref(lineage) or not self._valid_digest(workspace_digest):
            raise RunTransitionError("durable REVIEW rework source identity is malformed")
        return ReviewReworkContext(
            digest=str(digest),
            acceptance_ids=ids,
            finding=normalized,
            base_source_lineage_ref=str(lineage),
            workspace_digest=str(workspace_digest),
        )

    def review_rework_context_for_run(self, run: EngineeringRun) -> ReviewReworkContext | None:
        for attempt in reversed(run.attempts):
            if attempt.stage != WorkflowStage.REVIEW.value or attempt.status != AttemptStatus.RESUMED.value:
                continue
            try:
                evidence = json.loads(attempt.evidence_json or "{}")
            except (TypeError, json.JSONDecodeError) as exc:
                raise RunTransitionError("durable REVIEW control evidence is malformed") from exc
            if isinstance(evidence, dict) and evidence.get("review_rework_version") == "review-rework-v1":
                return self._context_from_rework_attempt(attempt)
        return None

    def _validate_plan_rework_context(self, run: EngineeringRun, evidence: dict[str, object]) -> None:
        context = self.review_rework_context_for_run(run)
        keys = {"review_rework_context_digest", "review_rework_acceptance_ids"}
        if context is None:
            if any(key in evidence for key in keys):
                raise ProtectedEvidenceError("PLAN asserted REVIEW rework context without durable human control")
            return
        if evidence.get("review_rework_context_digest") != context.digest:
            raise ProtectedEvidenceError("PLAN REVIEW rework context digest is stale")
        raw_ids = evidence.get("review_rework_acceptance_ids")
        if not isinstance(raw_ids, list) or raw_ids != list(context.acceptance_ids):
            raise ProtectedEvidenceError("PLAN REVIEW rework acceptance identity is stale")

    def review_rework(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
        acceptance_ids: list[str],
        finding: str,
    ) -> RunOperationResult:
        run = self.get(run_id)
        specification = self._bound_work_specification(run, require_project=self.require_project_binding)
        existing = self.runs.find_operation(run.id, operation_key)
        if existing is not None:
            if existing.stage != WorkflowStage.REVIEW.value or existing.status != AttemptStatus.RESUMED.value:
                raise RunTransitionError("REVIEW rework operation key is already bound to another operation")
            self._context_from_rework_attempt(existing)
            return self._result(RecordedMutation(run=self.get(run.id), attempt=existing, replayed=True))

        self._require_revision(run, expected_revision)
        try:
            state = WorkflowStage(run.state)
        except ValueError as exc:
            raise RunTransitionError(f"unknown durable run state {run.state}") from exc
        target = self.policy.validate_review_rework(state)
        if not run.project_id:
            raise RunTransitionError("REVIEW rework requires a Project-bound Engineering Run")

        if not isinstance(acceptance_ids, list) or not acceptance_ids or len(acceptance_ids) > 32:
            raise RunTransitionError("REVIEW rework requires 1 to 32 affected acceptance IDs")
        if not all(isinstance(item, str) and item for item in acceptance_ids):
            raise RunTransitionError("REVIEW rework acceptance IDs are malformed")
        if len(acceptance_ids) != len(set(acceptance_ids)):
            raise RunTransitionError("REVIEW rework acceptance IDs contain duplicates")
        required = required_acceptance_ids(specification)
        if not set(acceptance_ids) <= required:
            raise RunTransitionError("REVIEW rework references acceptance outside the approved Work Specification")
        canonical_ids = tuple(sorted(acceptance_ids))
        normalized_finding = self._normalize_review_rework_finding(finding)
        lineage, workspace_digest = self._latest_reviewed_implementation(run)
        digest = self._review_rework_digest(canonical_ids, normalized_finding)
        evidence = {
            "review_rework_version": "review-rework-v1",
            "review_rework_context_digest": digest,
            "acceptance_ids_rework": list(canonical_ids),
            "finding": normalized_finding,
            "project_ref": run.project_id,
            "run_id": run.id,
            "base_source_lineage_ref": lineage,
            "workspace_digest": workspace_digest,
            "protected_stage_authority": False,
            "source_mutation": False,
            "review_completion_authority": False,
            "production_deployment_authority": False,
        }
        mutation = self.runs.record(
            run,
            stage=WorkflowStage.REVIEW.value,
            operation_key=operation_key,
            status=AttemptStatus.RESUMED.value,
            next_state=target.value,
            evidence=evidence,
            program_id="protected-review-rework-v1",
            tool_id="human-review-control-v1",
        )
        return self._result(mutation)

    def acceptance_verification_scope_for_run(self, run: EngineeringRun) -> str | None:
        implementation_index: int | None = None
        base_source_lineage_ref: str | None = None
        for index in range(len(run.attempts) - 1, -1, -1):
            attempt = run.attempts[index]
            if attempt.stage != WorkflowStage.IMPLEMENT.value or attempt.status != AttemptStatus.PASSED.value:
                continue
            try:
                implementation = json.loads(attempt.evidence_json or "{}")
            except (TypeError, json.JSONDecodeError):
                return None
            if not isinstance(implementation, dict):
                return None
            project_ref = implementation.get("project_ref")
            base_ref = implementation.get("base_source_lineage_ref")
            source_ref = implementation.get("source_lineage_ref")
            if project_ref is None and base_ref is None and source_ref is None:
                return None
            if (
                not isinstance(project_ref, str)
                or project_ref != run.project_id
                or not isinstance(base_ref, str)
                or not base_ref.startswith("src:")
                or not isinstance(source_ref, str)
                or not source_ref.startswith("src:")
            ):
                return None
            implementation_index = index
            base_source_lineage_ref = base_ref
            break
        if implementation_index is None or base_source_lineage_ref is None:
            return None
        for attempt in reversed(run.attempts[:implementation_index]):
            if attempt.stage != WorkflowStage.PLAN.value or attempt.status != AttemptStatus.PASSED.value:
                continue
            try:
                evidence = json.loads(attempt.evidence_json or "{}")
            except (TypeError, json.JSONDecodeError):
                return None
            if not isinstance(evidence, dict):
                return None
            expected = {
                "project_id": run.project_id,
                "run_id": run.id,
                "work_specification_id": run.work_specification_id,
                "work_specification_revision": run.work_specification_revision,
                "work_specification_digest": run.work_specification_digest,
                "base_source_lineage_ref": base_source_lineage_ref,
            }
            if any(evidence.get(key) != value for key, value in expected.items()):
                return None
            try:
                contract = ExecutionContractIdentity.from_evidence(evidence).resolve()
            except ValidationProfileError:
                return None
            if (
                contract.contract_id is ExecutionContractCode.STATIC_WEB
                and contract.binding_reason is ExecutionBindingReason.GREENFIELD_STATIC_WEB
            ):
                return STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE
            return None
        return None

    def complete_stage(
        self,
        *,
        run_id: str,
        stage: WorkflowStage,
        operation_key: str,
        expected_revision: int,
        passed: bool,
        evidence: dict | None = None,
        failure_code: str | None = None,
        program_id: str | None = None,
        model_id: str | None = None,
        tool_id: str | None = None,
    ) -> RunOperationResult:
        run = self.get(run_id)
        self._bound_work_specification(run, require_project=self.require_project_binding)
        replay = self._idempotent_replay(run, operation_key)
        if replay is not None:
            return replay
        self._require_revision(run, expected_revision)

        specification = self._bound_work_specification(
            run,
            require_project=self.require_project_binding,
        )
        required = required_acceptance_ids(specification)

        try:
            current = WorkflowStage(run.state)
        except ValueError as exc:
            raise RunTransitionError(f"unknown durable run state {run.state}") from exc

        passing = {WorkflowStage(value) for value in self.runs.passing_stage_names(run.id)}
        self.policy.validate_stage_attempt(
            current_state=current,
            attempted_stage=stage,
            passing_stages=passing,
        )

        if passed:
            protected = evidence or {}
            if stage is WorkflowStage.SPECIFY:
                validate_specification_binding(
                    protected,
                    specification_id=specification.id,
                    specification_revision=specification.revision,
                    specification_digest=run.work_specification_digest or "",
                    required_acceptance_ids=required,
                )
            elif stage is WorkflowStage.PLAN:
                validate_plan(protected, required)
                self._validate_plan_rework_context(run, protected)
            elif stage is WorkflowStage.IMPLEMENT:
                validate_implementation(protected)
            elif stage is WorkflowStage.BUILD:
                validate_execution(protected, required, acceptance_key="acceptance_ids_targeted")
            elif stage in {WorkflowStage.TEST, WorkflowStage.VERIFY}:
                if self.acceptance_verification_scope_for_run(run) == STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE:
                    validate_structural_execution(protected, required)
                else:
                    validate_execution(protected, required, acceptance_key="acceptance_ids_verified")
            elif stage is WorkflowStage.REVIEW:
                implementation_attempts = [
                    item for item in run.attempts
                    if item.stage == WorkflowStage.IMPLEMENT.value and item.status == AttemptStatus.PASSED.value
                ]
                if not implementation_attempts:
                    raise RunTransitionError("REVIEW requires durable IMPLEMENT evidence")
                implementation = json.loads(implementation_attempts[-1].evidence_json)
                validate_review(protected, required, str(implementation.get("workspace_digest", "")))

        if passed:
            target = self.policy.success_target(stage)
            mutation = self.runs.record(
                run,
                stage=stage.value,
                operation_key=operation_key,
                status=AttemptStatus.PASSED.value,
                next_state=target.value,
                evidence=evidence,
                program_id=program_id,
                model_id=model_id,
                tool_id=tool_id,
            )
        else:
            code = failure_code or f"{stage.value}_FAILED"
            mutation = self.runs.record(
                run,
                stage=stage.value,
                operation_key=operation_key,
                status=AttemptStatus.FAILED.value,
                next_state=WorkflowStage.FAILED.value,
                resume_stage=stage.value,
                evidence=evidence,
                failure_code=code,
                program_id=program_id,
                model_id=model_id,
                tool_id=tool_id,
            )
        return self._result(mutation)

    def pause(self, *, run_id: str, operation_key: str, expected_revision: int) -> RunOperationResult:
        run = self.get(run_id)
        self._bound_work_specification(run, require_project=self.require_project_binding)
        replay = self._idempotent_replay(run, operation_key)
        if replay is not None:
            return replay
        self._require_revision(run, expected_revision)
        state = WorkflowStage(run.state)
        self.policy.validate_pause(state)
        mutation = self.runs.record(
            run,
            stage=state.value,
            operation_key=operation_key,
            status=AttemptStatus.PAUSED.value,
            next_state=WorkflowStage.PAUSED.value,
            resume_stage=state.value,
        )
        return self._result(mutation)

    def resume(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
        refresh_plan: bool = False,
    ) -> RunOperationResult:
        run = self.get(run_id)
        self._bound_work_specification(run, require_project=self.require_project_binding)
        replay = self._idempotent_replay(run, operation_key)
        if replay is not None:
            return replay
        self._require_revision(run, expected_revision)
        state = WorkflowStage(run.state)
        resume_stage = WorkflowStage(run.resume_stage) if run.resume_stage else None
        target = self.policy.validate_resume(
            state,
            resume_stage,
            refresh_plan=refresh_plan,
        )
        evidence = None
        if refresh_plan:
            evidence = {
                "plan_refresh_authorized": True,
                "prior_resume_stage": resume_stage.value if resume_stage is not None else None,
            }
        mutation = self.runs.record(
            run,
            stage=target.value,
            operation_key=operation_key,
            status=AttemptStatus.RESUMED.value,
            next_state=target.value,
            resume_stage=None,
            evidence=evidence,
        )
        return self._result(mutation)

    def cancel(self, *, run_id: str, operation_key: str, expected_revision: int) -> RunOperationResult:
        return self._terminal_control(
            run_id=run_id,
            operation_key=operation_key,
            expected_revision=expected_revision,
            target=WorkflowStage.CANCELLED,
            status=AttemptStatus.CANCELLED,
        )

    def require_spec_amendment(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
    ) -> RunOperationResult:
        return self._terminal_control(
            run_id=run_id,
            operation_key=operation_key,
            expected_revision=expected_revision,
            target=WorkflowStage.SPEC_AMENDMENT,
            status=AttemptStatus.SPEC_AMENDMENT,
        )

    def _terminal_control(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
        target: WorkflowStage,
        status: AttemptStatus,
    ) -> RunOperationResult:
        run = self.get(run_id)
        self._bound_work_specification(run, require_project=self.require_project_binding)
        replay = self._idempotent_replay(run, operation_key)
        if replay is not None:
            return replay
        self._require_revision(run, expected_revision)
        state = WorkflowStage(run.state)
        self.policy.validate_control(state)
        stage = state if state in ACTIVE_STAGES else WorkflowStage(run.resume_stage or WorkflowStage.SPECIFY.value)
        mutation = self.runs.record(
            run,
            stage=stage.value,
            operation_key=operation_key,
            status=status.value,
            next_state=target.value,
            resume_stage=None,
        )
        return self._result(mutation)

    def _result(self, mutation: RecordedMutation) -> RunOperationResult:
        self._emit_attempt_result(mutation)
        self._emit_replay(mutation)
        self._emit_review_required(mutation.run, mutation.attempt.id)
        return RunOperationResult(
            run=mutation.run,
            attempt_id=mutation.attempt.id,
            replayed=mutation.replayed,
        )
