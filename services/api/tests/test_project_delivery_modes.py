from __future__ import annotations

from types import SimpleNamespace

import pytest

from parallax_api.code.runtime_composition import EngineeringRuntimeComposition
from parallax_api.code.source_only_delivery import SourceOnlyDeliveryResult, SourceOnlyLineageDelivery
from parallax_api.projects.schemas import ProjectDeliveryModeUpdate
from parallax_api.projects.service import ProjectDeliveryModeConflictError, ProjectService
from parallax_api.code.run_events import RunEventSubsystem


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
LINEAGE_ID = "src:" + "a" * 64


class FakeProjectRepository:
    def __init__(self, *, states=frozenset({"PLAN"}), mode="vercel-preview"):
        self.project = SimpleNamespace(id=PROJECT_ID, delivery_mode=mode)
        self.states = frozenset(states)
        self.updated: list[str] = []

    def get_for_owner(self, project_id, owner_subject):
        return self.project if project_id == PROJECT_ID and owner_subject == "owner:test" else None

    def nonterminal_run_states(self, project_id):
        assert project_id == PROJECT_ID
        return self.states

    def update_delivery_mode(self, project, delivery_mode):
        self.updated.append(delivery_mode)
        project.delivery_mode = delivery_mode
        return project


def test_delivery_mode_can_change_while_run_is_still_plan() -> None:
    repository = FakeProjectRepository(states={"PLAN"})
    project = ProjectService(repository).update_delivery_mode(
        project_id=PROJECT_ID,
        owner_subject="owner:test",
        request=ProjectDeliveryModeUpdate(delivery_mode="source-only"),
    )
    assert project.delivery_mode == "source-only"
    assert repository.updated == ["source-only"]


def test_delivery_mode_is_locked_after_implementation_begins() -> None:
    repository = FakeProjectRepository(states={"IMPLEMENT"})
    with pytest.raises(ProjectDeliveryModeConflictError, match="locked"):
        ProjectService(repository).update_delivery_mode(
            project_id=PROJECT_ID,
            owner_subject="owner:test",
            request=ProjectDeliveryModeUpdate(delivery_mode="source-only"),
        )
    assert repository.updated == []


def test_delivery_mode_update_is_idempotent() -> None:
    repository = FakeProjectRepository(states={"IMPLEMENT"}, mode="source-only")
    project = ProjectService(repository).update_delivery_mode(
        project_id=PROJECT_ID,
        owner_subject="owner:test",
        request=ProjectDeliveryModeUpdate(delivery_mode="source-only"),
    )
    assert project.delivery_mode == "source-only"
    assert repository.updated == []


def test_source_only_success_event_contains_no_vercel_claims() -> None:
    events = []
    service = SimpleNamespace(event_sink=object(), emit_event=events.append)
    runtime = object.__new__(EngineeringRuntimeComposition)
    runtime.service = service
    runtime.source_delivery = SimpleNamespace(delivery=object.__new__(SourceOnlyLineageDelivery))

    result = SourceOnlyDeliveryResult(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        repository_identity_digest="b" * 64,
        lineage_id=LINEAGE_ID,
        content_digest="c" * 64,
        handoff_id="handoff:" + "d" * 64,
    )
    runtime._emit_delivery_success(
        result,
        SimpleNamespace(project_id=PROJECT_ID, id=RUN_ID, updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)),
    )

    assert len(events) == 1
    event = events[0]
    assert event.subsystem is RunEventSubsystem.SOURCE_LINEAGE
    assert event.evidence_ref == result.handoff_id
    assert event.metadata["delivery_action_count"] == 0
    assert "Vercel" not in event.summary
