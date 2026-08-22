from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.db import Base, make_engine
from parallax_api.projects.repository import ProjectConflictError, ProjectRepository
from parallax_api.projects.schemas import ProjectCreate
from parallax_api.projects.service import ProjectNotFoundError, ProjectService


def project_session_factory(tmp_path):
    database = tmp_path / "projects.db"
    engine = make_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_project_identity_persists_across_sessions(tmp_path):
    Session = project_session_factory(tmp_path)

    with Session() as session:
        service = ProjectService(ProjectRepository(session))
        created = service.create(
            owner_subject="owner-a",
            request=ProjectCreate(
                name="Inventory Console",
                description="Internal inventory application",
                repository_ref="github:Ryan9876/inventory-console",
            ),
        )
        project_id = created.id
        workspace_ref = created.workspace_ref
        assert created.slug == "inventory-console"
        assert workspace_ref == f"project:{project_id}"
        assert created.repository_ref == "github:Ryan9876/inventory-console"

    with Session() as session:
        loaded = ProjectService(ProjectRepository(session)).get(
            project_id=project_id,
            owner_subject="owner-a",
        )
        assert loaded.id == project_id
        assert loaded.workspace_ref == workspace_ref
        assert loaded.name == "Inventory Console"
        assert loaded.repository_ref == "github:Ryan9876/inventory-console"


def test_project_repository_isolates_owners_and_allows_owner_local_slugs(tmp_path):
    Session = project_session_factory(tmp_path)

    with Session() as session:
        service = ProjectService(ProjectRepository(session))
        first = service.create(
            owner_subject="owner-a",
            request=ProjectCreate(name="Portal", slug="portal"),
        )
        second = service.create(
            owner_subject="owner-b",
            request=ProjectCreate(name="Portal", slug="portal"),
        )

        assert [item.id for item in service.list(owner_subject="owner-a")] == [first.id]
        assert [item.id for item in service.list(owner_subject="owner-b")] == [second.id]

        with pytest.raises(ProjectNotFoundError):
            service.get(project_id=first.id, owner_subject="owner-b")


def test_same_owner_duplicate_slug_or_repository_is_conflict(tmp_path):
    Session = project_session_factory(tmp_path)

    with Session() as session:
        service = ProjectService(ProjectRepository(session))
        service.create(
            owner_subject="owner-a",
            request=ProjectCreate(
                name="Portal",
                slug="portal",
                repository_ref="github:Ryan9876/portal",
            ),
        )

        with pytest.raises(ProjectConflictError):
            service.create(
                owner_subject="owner-a",
                request=ProjectCreate(name="Other", slug="portal"),
            )

        with pytest.raises(ProjectConflictError):
            service.create(
                owner_subject="owner-a",
                request=ProjectCreate(
                    name="Other",
                    slug="other",
                    repository_ref="github:Ryan9876/portal",
                ),
            )

        assert len(service.list(owner_subject="owner-a")) == 1


def test_project_input_contract_rejects_paths_urls_credentials_and_bad_slugs():
    with pytest.raises(ValueError):
        ProjectCreate(name="Bad", repository_ref="https://github.com/Ryan9876/parallax")
    with pytest.raises(ValueError):
        ProjectCreate(name="Bad", repository_ref="github:user@example.com/repo")
    with pytest.raises(ValueError):
        ProjectCreate(name="Bad", repository_ref="github:../repo")
    with pytest.raises(ValueError):
        ProjectCreate(name="Bad", slug="../escape")

    request = ProjectCreate(
        name="  Valid Project  ",
        slug="valid-project",
        description="  useful metadata  ",
        repository_ref="github:Ryan9876/parallax",
    )
    assert request.name == "Valid Project"
    assert request.description == "useful metadata"
    assert request.repository_ref == "github:Ryan9876/parallax"
