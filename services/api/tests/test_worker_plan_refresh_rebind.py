from __future__ import annotations

import json
from uuid import uuid4

import pytest

from parallax_api.code.worker_recovery import WorkerCheckpoint, WorkerCheckpointError, validate_checkpoint
from parallax_api.models import EngineeringAttempt, EngineeringRun


OLD_PLAN = "a" * 64
NEW_PLAN = "b" * 64
OTHER_PLAN = "c" * 64
SPEC_DIGEST = "d" * 64


def _run() -> EngineeringRun:
    return EngineeringRun(
        id=str(uuid4()),
        conversation_id=str(uuid4()),
        spec_id="P2-V0.23.14",
        project_id=str(uuid4()),
        work_specification_id=str(uuid4()),
        work_specification_revision=1,
        work_specification_digest=SPEC_DIGEST,
        state="IMPLEMENT",
        revision=5,
    )


def _attempt(run: EngineeringRun, *, number: int, status: str, evidence: dict[str, object]) -> EngineeringAttempt:
    return EngineeringAttempt(
        id=str(uuid4()),
        run_id=run.id,
        stage="PLAN",
        attempt_number=number,
        operation_key=f"plan-{number}-{status.lower()}",
        status=status,
        evidence_json=json.dumps(evidence, sort_keys=True),
    )


def _checkpoint(run: EngineeringRun, plan_id: str) -> WorkerCheckpoint:
    return WorkerCheckpoint(
        project_id=run.project_id or "",
        run_id=run.id,
        work_specification_id=run.work_specification_id or "",
        work_specification_revision=int(run.work_specification_revision or 0),
        work_specification_digest=run.work_specification_digest or "",
        plan_ref=f"agentic-plan:{plan_id}",
        current_step="AGENT_DISPATCH",
    )


def test_plan_reference_change_remains_denied_without_human_refresh() -> None:
    run = _run()
    run.attempts = [
        _attempt(run, number=1, status="PASSED", evidence={"team_plan_id": OLD_PLAN}),
    ]

    with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
        validate_checkpoint(
            run,
            _checkpoint(run, NEW_PLAN),
            existing_plan_ref=f"agentic-plan:{OLD_PLAN}",
        )


def test_human_refresh_authorizes_only_exact_new_protected_plan() -> None:
    run = _run()
    run.attempts = [
        _attempt(run, number=1, status="PASSED", evidence={"team_plan_id": OLD_PLAN}),
        _attempt(run, number=2, status="RESUMED", evidence={"plan_refresh_authorized": True}),
        _attempt(run, number=3, status="PASSED", evidence={"team_plan_id": NEW_PLAN}),
    ]

    payload = validate_checkpoint(
        run,
        _checkpoint(run, NEW_PLAN),
        existing_plan_ref=f"agentic-plan:{OLD_PLAN}",
    )
    assert payload["plan_ref"] == f"agentic-plan:{NEW_PLAN}"

    with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
        validate_checkpoint(
            run,
            _checkpoint(run, OTHER_PLAN),
            existing_plan_ref=f"agentic-plan:{OLD_PLAN}",
        )


def test_incomplete_or_malformed_refresh_evidence_fails_closed() -> None:
    scenarios = (
        [
            ("PASSED", {"team_plan_id": OLD_PLAN}),
            ("RESUMED", {"plan_refresh_authorized": False}),
            ("PASSED", {"team_plan_id": NEW_PLAN}),
        ],
        [
            ("PASSED", {"team_plan_id": OLD_PLAN}),
            ("RESUMED", {"plan_refresh_authorized": True}),
        ],
        [
            ("PASSED", {"team_plan_id": OLD_PLAN}),
            ("RESUMED", {"plan_refresh_authorized": True}),
            ("PASSED", {"team_plan_id": "not-a-digest"}),
        ],
    )

    for entries in scenarios:
        run = _run()
        run.attempts = [
            _attempt(run, number=index, status=status, evidence=evidence)
            for index, (status, evidence) in enumerate(entries, start=1)
        ]
        with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
            validate_checkpoint(
                run,
                _checkpoint(run, NEW_PLAN),
                existing_plan_ref=f"agentic-plan:{OLD_PLAN}",
            )


def test_newer_refresh_without_success_invalidates_prior_rebind_authority() -> None:
    run = _run()
    run.attempts = [
        _attempt(run, number=1, status="PASSED", evidence={"team_plan_id": OLD_PLAN}),
        _attempt(run, number=2, status="RESUMED", evidence={"plan_refresh_authorized": True}),
        _attempt(run, number=3, status="PASSED", evidence={"team_plan_id": NEW_PLAN}),
        _attempt(run, number=4, status="RESUMED", evidence={"plan_refresh_authorized": True}),
    ]

    with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
        validate_checkpoint(
            run,
            _checkpoint(run, NEW_PLAN),
            existing_plan_ref=f"agentic-plan:{OLD_PLAN}",
        )


def test_post_rebind_checkpoint_is_immutable_without_another_complete_refresh() -> None:
    run = _run()
    run.attempts = [
        _attempt(run, number=1, status="PASSED", evidence={"team_plan_id": OLD_PLAN}),
        _attempt(run, number=2, status="RESUMED", evidence={"plan_refresh_authorized": True}),
        _attempt(run, number=3, status="PASSED", evidence={"team_plan_id": NEW_PLAN}),
    ]

    payload = validate_checkpoint(
        run,
        _checkpoint(run, NEW_PLAN),
        existing_plan_ref=f"agentic-plan:{NEW_PLAN}",
    )
    assert payload["plan_ref"] == f"agentic-plan:{NEW_PLAN}"

    with pytest.raises(WorkerCheckpointError, match="plan reference cannot change"):
        validate_checkpoint(
            run,
            _checkpoint(run, OTHER_PLAN),
            existing_plan_ref=f"agentic-plan:{NEW_PLAN}",
        )
