from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from parallax_api.tools.providers.common import ProviderClientError
from parallax_api.tools.providers.credentials import ProviderCredentialKind, ScopedBearerCredential
from parallax_api.tools.providers.vercel import VercelPreviewStatus
from parallax_api.tools.providers.vercel_client import VercelApiTarget, VercelPreviewRestClient


REPOSITORY_REF = "github:acme/example-app"
COMMIT = "1" * 40
TARGET = VercelApiTarget(
    vercel_project_ref="vercel:project:example-app",
    project_id="prj_example",
    project_name="example-app",
    team_id="team_example",
    repository_ref=REPOSITORY_REF,
    github_repo_id=12345,
    production_branch="main",
)


class VercelCredentials:
    def credential_for_project(self, vercel_project_ref: str) -> ScopedBearerCredential:
        return ScopedBearerCredential(
            provider="vercel",
            resource_ref=vercel_project_ref,
            kind=ProviderCredentialKind.VERCEL_OIDC,
            secret="test-only-vercel-scoped-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )


class PreviewStateTransport:
    def __init__(self, states: list[str]) -> None:
        self.states = list(states)
        self.reads = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v13/deployments/dpl_preview_1"
        assert request.headers["authorization"] == "Bearer test-only-vercel-scoped-token"
        index = min(self.reads, len(self.states) - 1)
        state = self.states[index]
        self.reads += 1
        return httpx.Response(
            200,
            json={
                "id": "dpl_preview_1",
                "readyState": state,
                "url": "example-app-run-1.vercel.app" if state == "READY" else None,
                "target": None,
                "project": {"id": "prj_example", "name": "example-app"},
                "gitSource": {
                    "type": "github",
                    "repoId": 12345,
                    "ref": "parallax/run-1",
                    "sha": COMMIT,
                },
            },
        )


def _client(handler: PreviewStateTransport, *, attempts: int) -> VercelPreviewRestClient:
    return VercelPreviewRestClient(
        VercelCredentials(),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(handler),
        preview_read_attempts=attempts,
        preview_poll_interval_seconds=0,
    )


def test_preview_read_waits_through_intermediate_states_until_ready() -> None:
    handler = PreviewStateTransport(["QUEUED", "BUILDING", "READY"])

    result = _client(handler, attempts=3).read_preview(
        TARGET.vercel_project_ref,
        "dpl_preview_1",
    )

    assert result.status is VercelPreviewStatus.READY
    assert result.url == "https://example-app-run-1.vercel.app"
    assert handler.reads == 3


def test_preview_read_fails_closed_when_bounded_wait_never_reaches_terminal_state() -> None:
    handler = PreviewStateTransport(["QUEUED", "BUILDING", "BUILDING"])

    with pytest.raises(ProviderClientError, match="PREVIEW_NOT_READY"):
        _client(handler, attempts=3).read_preview(
            TARGET.vercel_project_ref,
            "dpl_preview_1",
        )

    assert handler.reads == 3


def test_preview_read_returns_terminal_failure_without_waiting_for_exhaustion() -> None:
    handler = PreviewStateTransport(["QUEUED", "ERROR", "READY"])

    result = _client(handler, attempts=3).read_preview(
        TARGET.vercel_project_ref,
        "dpl_preview_1",
    )

    assert result.status is VercelPreviewStatus.ERROR
    assert handler.reads == 2
