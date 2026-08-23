from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from parallax_api.code.service import EngineeringRunNotFound, EngineeringRunService
from parallax_api.code.state_machine import SpecBindingError
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.schemas import EngineeringRunActivate, EngineeringRunCreate
from parallax_api.services.conversations import ConversationService
from parallax_api.services.work_specifications import WorkSpecificationService


def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'project-binding.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_project(projects: ProjectRepository, owner: str, slug: str):
    return projects.create(
        owner_subject=owner,
        slug=slug,
        name=slug.replace("-", " ").title(),
        description=None,
        repository_ref=None,
    )


def approved_spec(work_specs: WorkSpecificationRepository, conversation_id: str, label: str = "Bound contract"):
    draft = work_specs.create_draft(
        conversation_id=conversation_id,
        draft=WorkSpecificationDraft(
            title=label,
            objective="Implement only the Project-bound approved objective.",
            constraints=["Preserve Project isolation."],
            acceptance_criteria=[
                "Project identity remains consistent.",
                "Cross-Project execution remains denied.",
            ],
            risks=["Cross-Project execution would violate isolation."],
            open_questions=[],
            confidence=0.98,
            program_version="project-binding-test",
        ),
        model_id="test-model",
    )
    return work_specs.approve(draft)


def strict_conversations(session, owner: str):
    return ConversationService(
        ConversationRepository(session),
        ProjectRepository(session),
        owner_subject=owner,
        require_project_binding=True,
        active_spec_id="P2-V0.15.1",
    )


def strict_runs(session, owner: str):
    return EngineeringRunService(
        EngineeringRunRepository(session),
        ConversationRepository(session),
        WorkSpecificationRepository(session),
        ProjectRepository(session),
        owner_subject=owner,
        require_project_binding=True,
    )


def test_new_code_conversation_requires_owner_accessible_project_and_persists_identity(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        projects = ProjectRepository(session)
        project = create_project(projects, "owner-a", "alpha")
        service = strict_conversations(session, "owner-a")

        with pytest.raises(HTTPException) as missing:
            service.create("code")
        assert missing.value.status_code == 422

        conversation = service.create("code", project.id)
        conversation_id = conversation.id
        assert conversation.project_id == project.id
        assert conversation.project_binding_status == "PROJECT_BOUND"

        with pytest.raises(HTTPException) as denied:
            strict_conversations(session, "owner-b").create("code", project.id)
        assert denied.value.status_code == 404

    with Session() as session:
        restored = strict_conversations(session, "owner-a").get(conversation_id)
        assert restored.project_id == project.id
        assert restored.project_binding_status == "PROJECT_BOUND"


def test_project_bound_conversation_and_work_spec_access_is_owner_scoped_while_history_remains_readable(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        projects = ProjectRepository(session)
        project = create_project(projects, "owner-a", "bound")
        conversations = ConversationRepository(session)
        bound = strict_conversations(session, "owner-a").create("code", project.id)
        historical = conversations.create("code", spec_id="P2-V0.8.0")
        work_specs = WorkSpecificationRepository(session)
        specification = approved_spec(work_specs, bound.id)

        owner_b = strict_conversations(session, "owner-b")
        with pytest.raises(HTTPException) as hidden:
            owner_b.get(bound.id)
        assert hidden.value.status_code == 404
        assert owner_b.get(historical.id).project_binding_status == "HISTORICAL_UNBOUND"

        bound_specs = WorkSpecificationService(
            work_specs,
            conversations,
            owner_subject="owner-b",
        )
        with pytest.raises(HTTPException) as spec_hidden:
            bound_specs.latest(bound.id)
        assert spec_hidden.value.status_code == 404
        assert specification.conversation_id == bound.id


def test_new_engineering_run_derives_project_from_conversation_and_rejects_mismatches(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        projects = ProjectRepository(session)
        project_a = create_project(projects, "owner-a", "alpha-run")
        project_b = create_project(projects, "owner-a", "beta-run")
        conversations = strict_conversations(session, "owner-a")
        conversation_a = conversations.create("code", project_a.id)
        conversation_b = conversations.create("code", project_b.id)
        work_specs = WorkSpecificationRepository(session)
        spec_a = approved_spec(work_specs, conversation_a.id, "Project A contract")
        spec_b = approved_spec(work_specs, conversation_b.id, "Project B contract")
        runs = strict_runs(session, "owner-a")

        run = runs.activate_run(
            conversation_id=conversation_a.id,
            work_specification_id=spec_a.id,
        )
        assert run.project_id == project_a.id
        assert run.project_binding_status == "PROJECT_BOUND"
        assert run.workspace_ref is None

        with pytest.raises(SpecBindingError):
            runs.create_run(
                conversation_id=conversation_a.id,
                spec_id=conversation_a.spec_id,
                work_specification_id=spec_b.id,
            )

        with pytest.raises(EngineeringRunNotFound):
            strict_runs(session, "owner-b").get(run.id)


def test_historical_unbound_records_are_readable_but_cannot_start_strict_execution(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        conversations = ConversationRepository(session)
        historical = conversations.create("code", spec_id="P2-V0.8.0")
        spec = approved_spec(WorkSpecificationRepository(session), historical.id)
        strict = strict_runs(session, "owner-a")

        assert strict.latest_for_conversation(historical.id) is None
        with pytest.raises(SpecBindingError, match="Project-bound"):
            strict.activate_run(
                conversation_id=historical.id,
                work_specification_id=spec.id,
            )


def test_workspace_and_project_execution_identity_cannot_be_injected_by_request_contracts(tmp_path):
    with pytest.raises(ValidationError):
        EngineeringRunActivate.model_validate({
            "conversation_id": "conversation",
            "workspace_ref": "/tmp/escape",
        })
    with pytest.raises(ValidationError):
        EngineeringRunCreate.model_validate({
            "conversation_id": "conversation",
            "spec_id": "P2-V0.15.1",
            "work_specification_id": "specification",
            "project_id": "caller-project",
        })

    Session = session_factory(tmp_path)
    with Session() as session:
        project = create_project(ProjectRepository(session), "owner-a", "workspace-denial")
        conversation = strict_conversations(session, "owner-a").create("code", project.id)
        specification = approved_spec(WorkSpecificationRepository(session), conversation.id)
        with pytest.raises(SpecBindingError, match="workspace_ref"):
            strict_runs(session, "owner-a").activate_run(
                conversation_id=conversation.id,
                work_specification_id=specification.id,
                workspace_ref="project:caller-controlled",
            )


def test_project_runtime_binding_migration_is_nullable_forward_only_and_foreign_keyed():
    migration = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "20260822_0007_project_runtime_binding.sql"
    ).read_text()
    normalized = migration.lower()
    assert "alter table conversations" in normalized
    assert "alter table engineering_runs" in normalized
    assert normalized.count("project_id varchar(36) null") == 2
    assert "foreign key (project_id) references projects(id) on delete restrict" in normalized
    assert "update conversations" not in normalized
    assert "update engineering_runs" not in normalized
