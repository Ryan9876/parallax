from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from parallax_api.auth import AccessPrincipal, access_principal
from parallax_api.db import Base, get_session, make_engine
from parallax_api.projects.routes import router as projects_router


def project_client(tmp_path):
    database = tmp_path / "projects-api.db"
    engine = make_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    active_owner = {"subject": "owner-a"}

    app = FastAPI()
    app.include_router(projects_router)

    def session_override():
        with Session() as session:
            yield session

    def principal_override():
        return AccessPrincipal(
            subject=active_owner["subject"],
            role="owner",
            auth_method="test",
        )

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[access_principal] = principal_override
    return TestClient(app), active_owner


def test_create_list_read_and_cross_owner_not_found(tmp_path):
    client, active_owner = project_client(tmp_path)

    created = client.post(
        "/v1/projects",
        json={
            "name": "Network Investigator",
            "repository_ref": "github:Ryan9876/network-investigator",
        },
    )
    assert created.status_code == 201
    project = created.json()
    assert project["slug"] == "network-investigator"
    assert project["workspace_ref"] == f"project:{project['id']}"
    assert "owner_subject" not in project

    listed = client.get("/v1/projects")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [project["id"]]

    read = client.get(f"/v1/projects/{project['id']}")
    assert read.status_code == 200
    assert read.json()["workspace_ref"] == project["workspace_ref"]

    active_owner["subject"] = "owner-b"
    assert client.get("/v1/projects").json() == []
    hidden = client.get(f"/v1/projects/{project['id']}")
    assert hidden.status_code == 404
    assert hidden.json() == {"detail": "Project not found"}


def test_api_reports_validation_and_owner_local_conflicts(tmp_path):
    client, active_owner = project_client(tmp_path)

    invalid = client.post(
        "/v1/projects",
        json={"name": "Bad", "repository_ref": "https://github.com/Ryan9876/parallax"},
    )
    assert invalid.status_code == 422

    first = client.post(
        "/v1/projects",
        json={"name": "Portal", "slug": "portal", "repository_ref": "github:Ryan9876/portal"},
    )
    assert first.status_code == 201

    duplicate_slug = client.post(
        "/v1/projects",
        json={"name": "Duplicate", "slug": "portal"},
    )
    assert duplicate_slug.status_code == 409

    duplicate_repository = client.post(
        "/v1/projects",
        json={"name": "Other", "slug": "other", "repository_ref": "github:Ryan9876/portal"},
    )
    assert duplicate_repository.status_code == 409

    active_owner["subject"] = "owner-b"
    independent = client.post(
        "/v1/projects",
        json={"name": "Portal", "slug": "portal", "repository_ref": "github:Ryan9876/portal"},
    )
    assert independent.status_code == 201
