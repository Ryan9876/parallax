from __future__ import annotations

from dataclasses import dataclass

from .domain import ACTIVE_STAGES, SUCCESS_PATH, WorkflowStage


class RunTransitionError(ValueError):
    pass


class RevisionConflict(RunTransitionError):
    pass


class SpecBindingError(RunTransitionError):
    pass


@dataclass(frozen=True, slots=True)
class ProtectedRunPolicy:
    version: str = "code-run-policy-v0.5.0"

    def success_target(self, stage: WorkflowStage) -> WorkflowStage:
        if stage not in ACTIVE_STAGES:
            raise RunTransitionError(f"stage {stage.value} cannot be completed as a workflow step")
        index = SUCCESS_PATH.index(stage)
        return SUCCESS_PATH[index + 1]

    def required_predecessors(self, stage: WorkflowStage) -> tuple[WorkflowStage, ...]:
        if stage not in ACTIVE_STAGES:
            raise RunTransitionError(f"stage {stage.value} is not an executable workflow step")
        return SUCCESS_PATH[: SUCCESS_PATH.index(stage)]

    def validate_stage_attempt(
        self,
        *,
        current_state: WorkflowStage,
        attempted_stage: WorkflowStage,
        passing_stages: set[WorkflowStage],
    ) -> None:
        if current_state is not attempted_stage:
            raise RunTransitionError(
                f"cannot execute {attempted_stage.value} while run is {current_state.value}"
            )
        missing = [stage.value for stage in self.required_predecessors(attempted_stage) if stage not in passing_stages]
        if missing:
            raise RunTransitionError(
                f"cannot execute {attempted_stage.value}; missing protected passing evidence for {', '.join(missing)}"
            )

    def validate_pause(self, state: WorkflowStage) -> None:
        if state not in ACTIVE_STAGES:
            raise RunTransitionError(f"run in {state.value} cannot be paused")

    def validate_resume(
        self,
        state: WorkflowStage,
        resume_stage: WorkflowStage | None,
        *,
        refresh_plan: bool = False,
    ) -> WorkflowStage:
        if state not in {WorkflowStage.PAUSED, WorkflowStage.FAILED}:
            raise RunTransitionError(f"run in {state.value} cannot be resumed")
        if resume_stage not in ACTIVE_STAGES:
            raise RunTransitionError("run has no protected executable resume stage")
        if refresh_plan:
            if state is not WorkflowStage.FAILED or resume_stage is not WorkflowStage.IMPLEMENT:
                raise RunTransitionError(
                    "protected PLAN refresh requires explicit resume from FAILED IMPLEMENT"
                )
            return WorkflowStage.PLAN
        return resume_stage

    def validate_control(self, state: WorkflowStage) -> None:
        if state in {WorkflowStage.COMPLETE, WorkflowStage.CANCELLED, WorkflowStage.SPEC_AMENDMENT}:
            raise RunTransitionError(f"run in terminal state {state.value} cannot be mutated")
