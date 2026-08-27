from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from parallax_api.auth import AccessPrincipal, access_principal
from parallax_api.code.domain import TERMINAL_STAGES
from parallax_api.db import Base, get_session, make_engine
from parallax_api.models import Conversation, EngineeringRun
from parallax_api.projects.model import Project
from parallax_api.projects.repository import TERMINAL_RUN_STATES as PROJECT_TERMINAL_RUN_STATES
from parallax_api.projects.routes import router as projects_router
from parallax_api.repositories.conversations import (
    TERMINAL_RUN_STATES as CONVERSATION_TERMINAL_RUN_STATES,
)
from parallax_api.routes.conversations import router as conversations_router


def deletion_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'safe-deletion.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    actor = {"subject": "owner-a", "role": "owner"}

    app = FastAPI()
    app.include_router(projects_router)
    app.include_router(conversations_router)

    def session_override():
        with Session() as session:
            yield session

    def principal_override():
        return AccessPrincipal(
            subject=actor["subject"],
            role=actor["role"],
            auth_method="test",
        )

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[access_principal] = principal_override
    return TestClient(app), Session, actor


def create_project(client: TestClient, *, name: str = "Old Project", slug: str = "old-project") -> dict:
    response = client.post(
        "/v1/projects",
        json={
            "name": name,
            "slug": slug,
            "repository_ref": "github:Ryan9876/old-project",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_code_conversation(client: TestClient, project_id: str) -> dict:
    response = client.post(
        "/v1/conversations",
        json={"mode": "code", "project_id": project_id},
    )
    assert response.status_code == 200
    return response.json()


def add_run(Session, *, conversation_id: str, project_id: str | None, state: str) -> str:
    with Session() as session:
        run = EngineeringRun(
            conversation_id=conversation_id,
            project_id=project_id,
            spec_id="P2-V0.18.10",
            state=state,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def set_run_state(Session, run_id: str, state: str) -> None:
    with Session() as session:
        run = session.get(EngineeringRun, run_id)
        assert run is not None
        run.state = state
        session.add(run)
        session.commit()


def test_deletion_terminal_states_track_protected_runtime_contract():
    expected = frozenset(stage.value for stage in TERMINAL_STAGES)
    assert CONVERSATION_TERMINAL_RUN_STATES == expected
    assert PROJECT_TERMINAL_RUN_STATES == expected
    assert "SPEC_AMENDMENT" in expected
    assert "FAILED" not in expected


def test_delete_reason_conversation_hides_it_without_purging_row(tmp_path):
    client, Session, _ = deletion_context(tmp_path)
    conversation = client.post("/v1/conversations", json={"mode": "reason"}).json()

    deleted = client.delete(f"/v1/conversations/{conversation['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/v1/conversations/{conversation['id']}").status_code == 404
    assert conversation["id"] not in {item["id"] for item in client.get("/v1/conversations").json()}

    with Session() as session:
        persisted = session.get(Conversation, conversation["id"])
        assert persisted is not None
        assert persisted.deleted_at is not None


def test_delete_conversation_blocks_nonterminal_run_and_preserves_completed_run(tmp_path):
    client, Session, _ = deletion_context(tmp_path)
    project = create_project(client)
    conversation = create_code_conversation(client, project["id"])
    run_id = add_run(
        Session,
        conversation_id=conversation["id"],
        project_id=project["id"],
        state="PLAN",
    )

    blocked = client.delete(f"/v1/conversations/{conversation['id']}")
    assert blocked.status_code == 409
    assert "active engineering work" in blocked.json()["detail"]
    assert client.get(f"/v1/conversations/{conversation['id']}").status_code == 200

    set_run_state(Session, run_id, "COMPLETE")

    deleted = client.delete(f"/v1/conversations/{conversation['id']}")
    assert deleted.status_code == 204

    with Session() as session:
        assert session.get(Conversation, conversation["id"]) is not None
        assert session.get(EngineeringRun, run_id) is not None


def test_spec_amendment_is_terminal_for_conversation_and_project_deletion(tmp_path):
    client, Session, _ = deletion_context(tmp_path)
    project = create_project(client)
    conversation = create_code_conversation(client, project["id"])
    run_id = add_run(
        Session,
        conversation_id=conversation["id"],
        project_id=project["id"],
        state="SPEC_AMENDMENT",
    )

    deleted_conversation = client.delete(f"/v1/conversations/{conversation['id']}")
    assert deleted_conversation.status_code == 204

    deleted_project = client.delete(f"/v1/projects/{project['id']}")
    assert deleted_project.status_code == 204

    with Session() as session:
        assert session.get(EngineeringRun, run_id) is not None


def test_failed_run_remains_nonterminal_for_conversation_and_project_deletion(tmp_path):
    client, Session, _ = deletion_context(tmp_path)
    project = create_project(client)
    conversation = create_code_conversation(client, project["id"])
    add_run(
        Session,
        conversation_id=conversation["id"],
        project_id=project["id"],
        state="FAILED",
    )

    blocked_conversation = client.delete(f"/v1/conversations/{conversation['id']}")
    assert blocked_conversation.status_code == 409
    blocked_project = client.delete(f"/v1/projects/{project['id']}")
    assert blocked_project.status_code == 409


def test_historical_unbound_delete_requires_application_owner_role(tmp_path):
    client, Session, actor = deletion_context(tmp_path)
    conversation = client.post("/v1/conversations", json={"mode": "reason"}).json()

    actor["role"] = "member"
    assert client.get(f"/v1/conversations/{conversation['id']}").status_code == 200
    denied = client.delete(f"/v1/conversations/{conversation['id']}")
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Owner access required to delete historical unbound conversations"

    with Session() as session:
        persisted = session.get(Conversation, conversation["id"])
        assert persisted is not None
        assert persisted.deleted_at is None

    actor["role"] = "owner"
    deleted = client.delete(f"/v1/conversations/{conversation['id']}")
    assert deleted.status_code == 204


def test_project_bound_conversation_and_project_cross_owner_delete_are_hidden(tmp_path):
    client, Session, actor = deletion_context(tmp_path)
    project = create_project(client)
    conversation = create_code_conversation(client, project["id"])

    actor["subject"] = "owner-b"
    hidden_conversation = client.delete(f"/v1/conversations/{conversation['id']}")
    assert hidden_conversation.status_code == 404
    hidden_project = client.delete(f"/v1/projects/{project['id']}")
    assert hidden_project.status_code == 404

    with Session() as session:
        persisted_project = session.get(Project, project["id"])
        persisted_conversation = session.get(Conversation, conversation["id"])
        assert persisted_project is not None
        assert persisted_project.deleted_at is None
        assert persisted_conversation is not None
        assert persisted_conversation.deleted_at is None


def test_delete_project_hides_bound_history_preserves_evidence_and_allows_identity_reuse(tmp_path):
    client, Session, _ = deletion_context(tmp_path)
    project = create_project(client)
    conversation = create_code_conversation(client, project["id"])
    run_id = add_run(
        Session,
        conversation_id=conversation["id"],
        project_id=project["id"],
        state="COMPLETE",
    )

    deleted = client.delete(f"/v1/projects/{project['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/v1/projects/{project['id']}").status_code == 404
    assert project["id"] not in {item["id"] for item in client.get("/v1/projects").json()}
    assert client.get(f"/v1/conversations/{conversation['id']}").status_code == 404
    assert conversation["id"] not in {item["id"] for item in client.get("/v1/conversations").json()}

    with Session() as session:
        persisted_project = session.get(Project, project["id"])
        persisted_conversation = session.get(Conversation, conversation["id"])
        persisted_run = session.get(EngineeringRun, run_id)
        assert persisted_project is not None
        assert persisted_project.status == "deleted"
        assert persisted_project.deleted_at is not None
        assert persisted_conversation is not None
        assert persisted_conversation.deleted_at is None
        assert persisted_run is not None

    reused = client.post(
        "/v1/projects",
        json={
            "name": "Replacement Project",
            "slug": "old-project",
            "repository_ref": "github:Ryan9876/old-project",
        },
    )
    assert reused.status_code == 201
    assert reused.json()["id"] != project["id"]


def test_delete_project_blocks_nonterminal_run_and_cross_owner_delete_is_hidden(tmp_path):
    client, Session, actor = deletion_context(tmp_path)
    project = create_project(client)
    conversation = create_code_conversation(client, project["id"])
    add_run(
        Session,
        conversation_id=conversation["id"],
        project_id=project["id"],
        state="REVIEW",
    )

    blocked = client.delete(f"/v1/projects/{project['id']}")
    assert blocked.status_code == 409
    assert "active engineering work" in blocked.json()["detail"]

    actor["subject"] = "owner-b"
    hidden = client.delete(f"/v1/projects/{project['id']}")
    assert hidden.status_code == 404

    with Session() as session:
        persisted = session.scalar(select(Project).where(Project.id == project["id"]))
        assert persisted is not None
        assert persisted.deleted_at is None
