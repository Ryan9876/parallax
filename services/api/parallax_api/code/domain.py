from __future__ import annotations

from enum import Enum


class WorkflowStage(str, Enum):
    SPECIFY = "SPECIFY"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    BUILD = "BUILD"
    TEST = "TEST"
    VERIFY = "VERIFY"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    SPEC_AMENDMENT = "SPEC_AMENDMENT"
    CANCELLED = "CANCELLED"


class AttemptStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    CANCELLED = "CANCELLED"
    SPEC_AMENDMENT = "SPEC_AMENDMENT"


SUCCESS_PATH: tuple[WorkflowStage, ...] = (
    WorkflowStage.SPECIFY,
    WorkflowStage.PLAN,
    WorkflowStage.IMPLEMENT,
    WorkflowStage.BUILD,
    WorkflowStage.TEST,
    WorkflowStage.VERIFY,
    WorkflowStage.REVIEW,
    WorkflowStage.COMPLETE,
)

ACTIVE_STAGES = frozenset(SUCCESS_PATH[:-1])
TERMINAL_STAGES = frozenset(
    {WorkflowStage.COMPLETE, WorkflowStage.SPEC_AMENDMENT, WorkflowStage.CANCELLED}
)
