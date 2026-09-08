from fastapi import HTTPException
import pytest

from parallax_api.code.greenfield_composition import RepositoryAuthorizationRequiredError
from parallax_api.code.runtime_composition import RuntimeCompositionError
from parallax_api.code.worker_recovery import WorkerLeaseConflict
from parallax_api.routes.engineering_runs import invoke


def _authorization_failure():
    try:
        raise RepositoryAuthorizationRequiredError("exact repository consent required")
    except RepositoryAuthorizationRequiredError as cause:
        raise RuntimeCompositionError("repository-backed source bootstrap failed") from cause


def test_exact_repository_authorization_failure_is_structured_and_retry_safe() -> None:
    with pytest.raises(HTTPException) as captured:
        invoke(_authorization_failure)
    assert captured.value.status_code == 503
    assert captured.value.detail == {
        "message": "Repository authorization is required before Parallax can continue.",
        "code": "REPOSITORY_AUTHORIZATION_REQUIRED",
    }


def test_generic_runtime_failure_remains_generic() -> None:
    with pytest.raises(HTTPException) as captured:
        invoke(lambda: (_ for _ in ()).throw(RuntimeCompositionError("generic failure")))
    assert captured.value.status_code == 503
    assert captured.value.detail == "generic failure"


def test_active_autonomy_worker_conflict_is_structured_and_non_sensitive() -> None:
    with pytest.raises(HTTPException) as captured:
        invoke(lambda: (_ for _ in ()).throw(WorkerLeaseConflict("worker:secret-owner")))
    assert captured.value.status_code == 409
    assert captured.value.detail == {
        "message": "Parallax is already continuing this build. The current work is still in progress.",
        "code": "AUTONOMY_IN_PROGRESS",
    }
    assert "secret-owner" not in str(captured.value.detail)
