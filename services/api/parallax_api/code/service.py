from __future__ import annotations

from dataclasses import dataclass
import json

from ..models import Conversation, EngineeringRun, WorkSpecification
from ..projects.repository import ProjectRepository
from ..repositories.conversations import ConversationRepository
from ..repositories.engineering_runs import EngineeringRunRepository, RecordedMutation
from ..repositories.work_specifications import WorkSpecificationRepository
from .domain import ACTIVE_STAGES, TERMINAL_STAGES, AttemptStatus, WorkflowStage
from .state_machine import ProtectedRunPolicy, RevisionConflict, RunTransitionError, SpecBindingError
from .protected import (
    validate_execution,
    validate_implementation,
    validate_plan,
    validate_review,
    validate_specification_binding,
)
from .work_spec_binding import acceptance_map, required_acceptance_ids, work_specification_digest


class EngineeringRunNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class RunOperationResult:
    run: EngineeringRun
    attempt_id: str
    replayed: bool


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
    ):
        self.runs = run_repository
        self.conversations = conversation_repository
        self.work_specifications = work_specification_repository or WorkSpecificationRepository(run_repository.session)
        self.projects = project_repository
        self.owner_subject = owner_subject.strip() if owner_subject else None
        self.require_project_binding = require_project_binding
        self.policy = policy or ProtectedRunPolicy()

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
        return self.runs.create(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
            project_id=conversation.project_id,
            work_specification_id=specification.id,
            work_specification_revision=specification.revision,
            work_specification_digest=work_specification_digest(specification),
            workspace_ref=None if self.require_project_binding else workspace_ref,
        )

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
        return RunOperationResult(run=self.get(run.id), attempt_id=existing.id, replayed=True)

    @staticmethod
    def _require_revision(run: EngineeringRun, expected_revision: int) -> None:
        if run.revision != expected_revision:
            raise RevisionConflict(
                f"stale engineering run revision: expected {expected_revision}, current {run.revision}"
            )

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
            elif stage is WorkflowStage.IMPLEMENT:
                validate_implementation(protected)
            elif stage is WorkflowStage.BUILD:
                validate_execution(protected, required, acceptance_key="acceptance_ids_targeted")
            elif stage in {WorkflowStage.TEST, WorkflowStage.VERIFY}:
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

    def resume(self, *, run_id: str, operation_key: str, expected_revision: int) -> RunOperationResult:
        run = self.get(run_id)
        self._bound_work_specification(run, require_project=self.require_project_binding)
        replay = self._idempotent_replay(run, operation_key)
        if replay is not None:
            return replay
        self._require_revision(run, expected_revision)
        state = WorkflowStage(run.state)
        resume_stage = WorkflowStage(run.resume_stage) if run.resume_stage else None
        target = self.policy.validate_resume(state, resume_stage)
        mutation = self.runs.record(
            run,
            stage=target.value,
            operation_key=operation_key,
            status=AttemptStatus.RESUMED.value,
            next_state=target.value,
            resume_stage=None,
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

    @staticmethod
    def _result(mutation: RecordedMutation) -> RunOperationResult:
        return RunOperationResult(
            run=mutation.run,
            attempt_id=mutation.attempt.id,
            replayed=mutation.replayed,
        )
