from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from parallax_api.auth import AccessPrincipal, access_principal
from parallax_api.db import Base, get_session, make_engine
from parallax_api.models import Conversation, EngineeringRun
from parallax_api.projects.model import Project
from parallax_api.projects.routes import router as projects_router
from parallax_api.routes.conversations import router as conversations_router


def deletion_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'safe-deletion.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    owner = {"subject": "owner-a"}

    app = FastAPI()
    app.include_router(projects_router)
    app.include_router(conversations_router)

    def session_override():
        with Session() as session:
            yield session

    def principal_override():
        return AccessPrincipal(
            subject=owner["subject"],
            role="owner",
            auth_method="test",
        )

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[access_principal] = principal_override
    return TestClient(app), Session, owner


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


def add_run(Session, *, conversation_id: str, project_id: str, state: str) -> str:
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

    with Session() as session:
        run = session.get(EngineeringRun, run_id)
        assert run is not None
        run.state = "COMPLETE"
        session.add(run)
        session.commit()

    deleted = client.delete(f"/v1/conversations/{conversation['id']}")
    assert deleted.status_code == 204

    with Session() as session:
        assert session.get(Conversation, conversation["id"]) is not None
        assert session.get(EngineeringRun, run_id) is not None


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
    client, Session, owner = deletion_context(tmp_path)
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

    owner["subject"] = "owner-b"
    hidden = client.delete(f"/v1/projects/{project['id']}")
    assert hidden.status_code == 404

    with Session() as session:
        persisted = session.scalar(select(Project).where(Project.id == project["id"]))
        assert persisted is not None
        assert persisted.deleted_at is None
