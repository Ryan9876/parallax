from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from parallax_api.auth import AccessPrincipal, access_principal
from parallax_api.db import Base, get_session, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.routes.conversations import router as conversations_router
from parallax_api.routes.engineering_runs import router as engineering_runs_router
from parallax_api.routes.work_specifications import router as work_specifications_router


def api_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'project-binding-api.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    owner = {"subject": "owner-a"}

    app = FastAPI()
    app.include_router(conversations_router)
    app.include_router(work_specifications_router)
    app.include_router(engineering_runs_router)

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


def create_project(Session, owner: str, slug: str):
    with Session() as session:
        return ProjectRepository(session).create(
            owner_subject=owner,
            slug=slug,
            name=slug.title(),
            description=None,
            repository_ref=None,
        )


def approve_spec(Session, conversation_id: str):
    with Session() as session:
        repository = WorkSpecificationRepository(session)
        draft = repository.create_draft(
            conversation_id=conversation_id,
            draft=WorkSpecificationDraft(
                title="API project binding",
                objective="Prove API Project identity binding.",
                constraints=["Keep Project identity server controlled."],
                acceptance_criteria=[
                    "The run inherits the conversation Project.",
                    "A different owner cannot access the bound runtime records.",
                ],
                risks=["Cross-owner access must fail closed."],
                open_questions=[],
                confidence=0.99,
                program_version="project-binding-api-test",
            ),
            model_id="test-model",
        )
        return repository.approve(draft)


def test_code_conversation_api_requires_owner_project_and_reports_binding_state(tmp_path):
    client, Session, owner = api_context(tmp_path)
    project = create_project(Session, "owner-a", "api-alpha")

    missing = client.post("/v1/conversations", json={"mode": "code"})
    assert missing.status_code == 422

    created = client.post(
        "/v1/conversations",
        json={"mode": "code", "project_id": project.id},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["project_id"] == project.id
    assert payload["project_binding_status"] == "PROJECT_BOUND"

    owner["subject"] = "owner-b"
    hidden = client.get(f"/v1/conversations/{payload['id']}")
    assert hidden.status_code == 404
    denied_create = client.post(
        "/v1/conversations",
        json={"mode": "code", "project_id": project.id},
    )
    assert denied_create.status_code == 404


def test_historical_reason_and_unbound_conversation_api_compatibility_is_explicit(tmp_path):
    client, _, _ = api_context(tmp_path)
    created = client.post("/v1/conversations", json={"mode": "reason"})
    assert created.status_code == 200
    assert created.json()["project_id"] is None
    assert created.json()["project_binding_status"] == "HISTORICAL_UNBOUND"


def test_run_api_derives_project_and_rejects_workspace_or_cross_owner_access(tmp_path):
    client, Session, owner = api_context(tmp_path)
    project = create_project(Session, "owner-a", "api-run")
    conversation = client.post(
        "/v1/conversations",
        json={"mode": "code", "project_id": project.id},
    ).json()
    specification = approve_spec(Session, conversation["id"])

    injected = client.post(
        "/v1/engineering-runs/activate",
        json={
            "conversation_id": conversation["id"],
            "work_specification_id": specification.id,
            "workspace_ref": "/tmp/caller-selected",
        },
    )
    assert injected.status_code == 422

    activated = client.post(
        "/v1/engineering-runs/activate",
        json={
            "conversation_id": conversation["id"],
            "work_specification_id": specification.id,
        },
    )
    assert activated.status_code == 200
    run = activated.json()
    assert run["project_id"] == project.id
    assert run["project_binding_status"] == "PROJECT_BOUND"
    assert run["workspace_ref"] is None

    latest_spec = client.get(
        f"/v1/conversations/{conversation['id']}/work-specifications/latest"
    )
    assert latest_spec.status_code == 200
    assert latest_spec.json()["id"] == specification.id

    owner["subject"] = "owner-b"
    assert client.get(f"/v1/engineering-runs/{run['id']}").status_code == 404
    assert client.get(
        f"/v1/conversations/{conversation['id']}/work-specifications/latest"
    ).status_code == 404
