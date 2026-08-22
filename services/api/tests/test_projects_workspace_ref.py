from parallax_api.projects.schemas import ProjectCreate
from parallax_api.projects.service import ProjectService
from parallax_api.projects.repository import ProjectRepository
from parallax_api.db import Base, make_engine
from sqlalchemy.orm import sessionmaker


def test_workspace_ref_is_opaque_project_identity_not_user_input(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'workspace-ref.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        project = ProjectService(ProjectRepository(session)).create(
            owner_subject="owner-a",
            request=ProjectCreate(name="Workspace Boundary"),
        )
        assert project.workspace_ref == f"project:{project.id}"
        assert "/" not in project.workspace_ref
        assert "\\" not in project.workspace_ref
