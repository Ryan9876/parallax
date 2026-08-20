from __future__ import annotations

from dataclasses import dataclass
import json

from ..models import EngineeringRun
from ..repositories.conversations import ConversationRepository
from ..repositories.engineering_runs import EngineeringRunRepository, RecordedMutation
from .domain import ACTIVE_STAGES, AttemptStatus, WorkflowStage
from .state_machine import ProtectedRunPolicy, RevisionConflict, RunTransitionError, SpecBindingError
from .protected import validate_execution, validate_implementation, validate_plan, validate_review


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
        *,
        policy: ProtectedRunPolicy | None = None,
    ):
        self.runs = run_repository
        self.conversations = conversation_repository
        self.policy = policy or ProtectedRunPolicy()

    def create_run(
        self,
        *,
        conversation_id: str,
        spec_id: str,
        workspace_ref: str | None = None,
    ) -> EngineeringRun:
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            raise EngineeringRunNotFound("conversation not found")
        if conversation.mode != "code":
            raise SpecBindingError("engineering runs require a Code conversation")
        if conversation.status == "SPEC_AMENDMENT":
            raise SpecBindingError("conversation requires a specification amendment before Code execution")
        if conversation.spec_id != spec_id:
            raise SpecBindingError(
                f"run spec {spec_id} does not match durable conversation spec {conversation.spec_id}"
            )
        return self.runs.create(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
            workspace_ref=workspace_ref,
        )

    def get(self, run_id: str) -> EngineeringRun:
        run = self.runs.get(run_id)
        if run is None:
            raise EngineeringRunNotFound("engineering run not found")
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
        replay = self._idempotent_replay(run, operation_key)
        if replay is not None:
            return replay
        self._require_revision(run, expected_revision)

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
            required = set(protected.get("required_acceptance_ids", []))
            if stage is WorkflowStage.PLAN:
                validate_plan(protected, required)
            elif stage is WorkflowStage.IMPLEMENT:
                validate_implementation(protected)
            elif stage in {WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY}:
                validate_execution(protected)
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
