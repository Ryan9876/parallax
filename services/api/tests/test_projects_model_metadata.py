from parallax_api.db import Base
from parallax_api.projects.model import Project


def test_project_model_is_registered_with_shared_metadata():
    assert Project.__table__ is Base.metadata.tables["projects"]
