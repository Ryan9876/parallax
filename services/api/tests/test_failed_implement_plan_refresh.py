from __future__ import annotations

import pytest

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.state_machine import ProtectedRunPolicy, RunTransitionError


def test_failed_implement_can_refresh_to_plan_only_when_explicitly_authorized():
    policy = ProtectedRunPolicy()

    assert policy.validate_resume(
        WorkflowStage.FAILED,
        WorkflowStage.IMPLEMENT,
        refresh_plan=True,
    ) is WorkflowStage.PLAN


def test_plan_refresh_cannot_be_used_from_paused_run():
    policy = ProtectedRunPolicy()

    with pytest.raises(RunTransitionError, match="FAILED IMPLEMENT"):
        policy.validate_resume(
            WorkflowStage.PAUSED,
            WorkflowStage.IMPLEMENT,
            refresh_plan=True,
        )


def test_plan_refresh_cannot_retarget_non_implement_failure():
    policy = ProtectedRunPolicy()

    with pytest.raises(RunTransitionError, match="FAILED IMPLEMENT"):
        policy.validate_resume(
            WorkflowStage.FAILED,
            WorkflowStage.TEST,
            refresh_plan=True,
        )


def test_normal_failed_resume_behavior_is_unchanged_without_refresh():
    policy = ProtectedRunPolicy()

    assert policy.validate_resume(
        WorkflowStage.FAILED,
        WorkflowStage.TEST,
    ) is WorkflowStage.TEST
