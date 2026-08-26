from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from parallax_api.code.service import EngineeringRunService
from parallax_api.code.state_machine import SpecBindingError
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.repository_identity import (
    find_repository_identity_conflict,
    normalize_github_repository_ref,
)
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.services.conversations import ConversationService
from parallax_api.services.work_specifications import WorkSpecificationService


def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'repository-identity.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def project(projects: ProjectRepository, *, repository_ref: str = "github:Ryan9876/parallax"):
    return projects.create(
        owner_subject="owner-a",
        slug="target",
        name="Target",
        description=None,
        repository_ref=repository_ref,
    )


def conversation(session, project_id: str, objective: str):
    service = ConversationService(
        ConversationRepository(session),
        ProjectRepository(session),
        owner_subject="owner-a",
        require_project_binding=True,
        active_spec_id="P2-V0.18.6",
    )
    created = service.create("code", project_id)
    service.append_follow_up(created.id, objective)
    return service.get(created.id)


def draft(work_specs: WorkSpecificationRepository, conversation_id: str, *, target: str):
    return work_specs.create_draft(
        conversation_id=conversation_id,
        draft=WorkSpecificationDraft(
            title=f"Create an About page for {target}",
            objective=f"Implement and verify an About page in {target}.",
            constraints=["Preserve the selected Project boundary."],
            acceptance_criteria=[
                "The About page is implemented.",
                "The About page is verified without changing repository authority.",
            ],
            risks=[],
            open_questions=[],
            confidence=0.95,
            program_version="repository-identity-test",
        ),
        model_id="test-model",
    )


def strict_runs(session):
    return EngineeringRunService(
        EngineeringRunRepository(session),
        ConversationRepository(session),
        WorkSpecificationRepository(session),
        ProjectRepository(session),
        owner_subject="owner-a",
        require_project_binding=True,
    )


def test_repository_identity_normalization_is_case_insensitive_and_protocol_agnostic():
    assert normalize_github_repository_ref("github:Ryan9876/Parallax") == "ryan9876/parallax"
    assert normalize_github_repository_ref("https://github.com/Ryan9876/Parallax.git") == "ryan9876/parallax"
    assert normalize_github_repository_ref("Ryan9876/Parallax") == "ryan9876/parallax"


def test_target_reference_conflicts_but_source_paths_and_dependency_context_do_not():
    conflict = find_repository_identity_conflict(
        canonical_repository_ref="github:Ryan9876/parallax",
        target_texts=("Create an About page for Ryan9876/ot-time.",),
    )
    assert conflict is not None
    assert conflict.requested_repository_refs == ("ryan9876/ot-time",)
    assert "github:ryan9876/parallax" in conflict.public_message
    assert "github:ryan9876/ot-time" in conflict.public_message

    assert find_repository_identity_conflict(
        canonical_repository_ref="github:Ryan9876/parallax",
        target_texts=("Update apps/client and use Ryan9876/shared-lib as a dependency.",),
    ) is None
    assert find_repository_identity_conflict(
        canonical_repository_ref="github:Ryan9876/parallax",
        target_texts=("Create an About page for Ryan9876/parallax.",),
    ) is None


def test_work_specification_approval_fails_closed_on_repository_target_mismatch(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        projects = ProjectRepository(session)
        selected = project(projects)
        bound = conversation(session, selected.id, "Create an About page for Ryan9876/ot-time")
        work_specs = WorkSpecificationRepository(session)
        specification = draft(work_specs, bound.id, target="Ryan9876/ot-time")
        service = WorkSpecificationService(
            work_specs,
            ConversationRepository(session),
            projects,
            owner_subject="owner-a",
        )

        with pytest.raises(HTTPException) as blocked:
            service.approve(specification.id)

        assert blocked.value.status_code == 409
        assert "selected Project is bound to github:ryan9876/parallax" in blocked.value.detail
        assert "Select or create the intended Project" in blocked.value.detail
        assert work_specs.get(specification.id).status == "DRAFT"


def test_correctly_selected_repository_can_be_approved(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        projects = ProjectRepository(session)
        selected = project(projects)
        bound = conversation(session, selected.id, "Create an About page for Ryan9876/parallax")
        work_specs = WorkSpecificationRepository(session)
        specification = draft(work_specs, bound.id, target="Ryan9876/parallax")
        service = WorkSpecificationService(
            work_specs,
            ConversationRepository(session),
            projects,
            owner_subject="owner-a",
        )

        approved = service.approve(specification.id)
        assert approved.status == "APPROVED"


def test_legacy_mismatched_approved_spec_cannot_activate_engineering_run(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        projects = ProjectRepository(session)
        selected = project(projects)
        bound = conversation(session, selected.id, "Create an About page for Ryan9876/ot-time")
        work_specs = WorkSpecificationRepository(session)
        mismatched = draft(work_specs, bound.id, target="Ryan9876/ot-time")
        approved = work_specs.approve(mismatched)  # simulate an approval created before the hotfix guard
        runs = strict_runs(session)

        with pytest.raises(SpecBindingError, match="Repository target conflict"):
            runs.activate_run(
                conversation_id=bound.id,
                work_specification_id=approved.id,
            )

        assert runs.latest_for_conversation(bound.id) is None
