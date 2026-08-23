from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json

import httpx

from parallax_api.tools.providers.common import AcceptedSourceLineage
from parallax_api.tools.providers.credentials import (
    ProviderCredentialKind,
    ScopedBearerCredential,
)
from parallax_api.tools.providers.github import GitHubCommitFile, GitHubProviderClient
from parallax_api.tools.providers.github_client import GitHubRestProviderClient
from parallax_api.tools.providers.vercel import VercelPreviewStatus, VercelProviderClient
from parallax_api.tools.providers.vercel_client import VercelApiTarget, VercelPreviewRestClient


PROJECT_ID = "7e643661-99d6-4b31-9af7-d86d30b01c14"
RUN_ID = "1cf43021-4653-4e9c-bf54-68fd7d72ea35"
REPOSITORY_REF = "github:acme/example-app"
BASE = "0" * 40
COMMIT = "1" * 40
TREE = "2" * 40
BLOB = "3" * 40
LINEAGE = AcceptedSourceLineage(
    PROJECT_ID,
    RUN_ID,
    "src:" + "a" * 64,
    "b" * 64,
)


class GitHubCredentials:
    def credential_for_repository(self, repository_ref: str) -> ScopedBearerCredential:
        return ScopedBearerCredential(
            provider="github",
            resource_ref=repository_ref,
            kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
            secret="test-only-github-installation-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
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


def _request_json(request: httpx.Request) -> dict[str, object]:
    return json.loads(request.content.decode("utf-8")) if request.content else {}


class GitHubHappyTransport:
    def __init__(self) -> None:
        self.branch_head: str | None = None
        self.commit_posts = 0
        self.pull_posts = 0

    @staticmethod
    def _ref(sha: str, branch: str) -> dict[str, object]:
        return {"ref": f"refs/heads/{branch}", "object": {"sha": sha, "type": "commit"}}

    @staticmethod
    def _pr(number: int, sha: str) -> dict[str, object]:
        repo = {"full_name": "acme/example-app"}
        return {
            "number": number,
            "state": "open",
            "html_url": f"https://github.com/acme/example-app/pull/{number}",
            "head": {"ref": "parallax/run-1", "sha": sha, "repo": repo},
            "base": {"ref": "main", "repo": repo},
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-only-github-installation-token"
        path = request.url.path

        if request.method == "GET" and path == "/repos/acme/example-app":
            return httpx.Response(200, json={"full_name": "acme/example-app", "default_branch": "main"})
        if request.method == "GET" and path == "/repos/acme/example-app/git/ref/heads/main":
            return httpx.Response(200, json=self._ref(BASE, "main"))
        if request.method == "GET" and path == f"/repos/acme/example-app/git/trees/{BASE}":
            return httpx.Response(
                200,
                json={
                    "sha": TREE,
                    "truncated": False,
                    "tree": [
                        {"path": "src", "mode": "040000", "type": "tree", "sha": TREE},
                        {"path": "src/app.py", "mode": "100644", "type": "blob", "sha": BLOB, "size": 15},
                    ],
                },
            )
        if request.method == "GET" and path == "/repos/acme/example-app/contents/src/app.py":
            content = b"print('hello')\n"
            return httpx.Response(
                200,
                json={
                    "type": "file",
                    "path": "src/app.py",
                    "size": len(content),
                    "encoding": "base64",
                    "content": base64.b64encode(content).decode("ascii"),
                },
            )
        if request.method == "GET" and path == "/repos/acme/example-app/git/ref/heads/parallax/run-1":
            if self.branch_head is None:
                return httpx.Response(404, json={"message": "not found"})
            return httpx.Response(200, json=self._ref(self.branch_head, "parallax/run-1"))
        if request.method == "POST" and path == "/repos/acme/example-app/git/refs":
            body = _request_json(request)
            assert body == {"ref": "refs/heads/parallax/run-1", "sha": BASE}
            self.branch_head = BASE
            return httpx.Response(201, json=self._ref(BASE, "parallax/run-1"))
        if request.method == "GET" and path == f"/repos/acme/example-app/git/commits/{BASE}":
            return httpx.Response(200, json={"sha": BASE, "message": "base", "tree": {"sha": TREE}, "parents": []})
        if request.method == "POST" and path == "/repos/acme/example-app/git/trees":
            body = _request_json(request)
            assert body["base_tree"] == TREE
            assert body["tree"][0]["path"] == "src/app.py"
            return httpx.Response(201, json={"sha": "4" * 40})
        if request.method == "POST" and path == "/repos/acme/example-app/git/commits":
            self.commit_posts += 1
            body = _request_json(request)
            assert body["parents"] == [BASE]
            assert body["author"]["date"] == "2000-01-01T00:00:00Z"
            assert f"Parallax-Lineage: {LINEAGE.lineage_id}" in body["message"]
            return httpx.Response(201, json={"sha": COMMIT})
        if request.method == "PATCH" and path == "/repos/acme/example-app/git/refs/heads/parallax/run-1":
            body = _request_json(request)
            assert body == {"sha": COMMIT, "force": False}
            self.branch_head = COMMIT
            return httpx.Response(200, json=self._ref(COMMIT, "parallax/run-1"))
        if request.method == "GET" and path == f"/repos/acme/example-app/git/commits/{COMMIT}":
            return httpx.Response(
                200,
                json={
                    "sha": COMMIT,
                    "message": GitHubRestProviderClient._lineage_message(LINEAGE),
                    "tree": {"sha": "4" * 40},
                    "parents": [{"sha": BASE}],
                },
            )
        if request.method == "GET" and path == "/repos/acme/example-app/pulls":
            if self.pull_posts:
                return httpx.Response(200, json=[self._pr(42, COMMIT)])
            return httpx.Response(200, json=[])
        if request.method == "POST" and path == "/repos/acme/example-app/pulls":
            self.pull_posts += 1
            body = _request_json(request)
            assert body["head"] == "parallax/run-1"
            assert body["base"] == "main"
            return httpx.Response(201, json=self._pr(42, COMMIT))
        if request.method == "GET" and path == "/repos/acme/example-app/pulls/42":
            return httpx.Response(200, json=self._pr(42, COMMIT))
        raise AssertionError(f"unexpected GitHub request: {request.method} {request.url}")


def test_github_concrete_client_matches_exact_protocol_and_is_idempotent() -> None:
    handler = GitHubHappyTransport()
    client: GitHubProviderClient = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    repository = client.resolve_repository(REPOSITORY_REF)
    assert repository.default_branch == "main"
    assert repository.head_revision == BASE

    tree = client.read_tree(REPOSITORY_REF, BASE, max_entries=512)
    assert tuple(entry.path for entry in tree.entries) == ("src", "src/app.py")

    source = client.read_file(REPOSITORY_REF, BASE, "src/app.py", max_bytes=256_000)
    assert source.content == "print('hello')\n"

    branch = client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE)
    assert branch.head_revision == BASE
    replay_branch = client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE)
    assert replay_branch == branch

    content = "print('updated')\n"
    commit_file = GitHubCommitFile(
        "src/app.py",
        content,
        __import__("hashlib").sha256(content.encode()).hexdigest(),
    )
    commit = client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (commit_file,),
    )
    assert commit.commit_revision == COMMIT
    assert handler.commit_posts == 1

    replay_commit = client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (commit_file,),
    )
    assert replay_commit == commit
    assert handler.commit_posts == 1

    pull_request = client.create_pull_request(
        REPOSITORY_REF,
        "parallax/run-1",
        COMMIT,
        "main",
        "Parallax change",
        "bounded body",
    )
    assert pull_request.number == 42
    replay_pull_request = client.create_pull_request(
        REPOSITORY_REF,
        "parallax/run-1",
        COMMIT,
        "main",
        "Parallax change",
        "bounded body",
    )
    assert replay_pull_request.number == 42
    assert handler.pull_posts == 1
    assert client.read_pull_request(REPOSITORY_REF, 42).head_revision == COMMIT


TARGET = VercelApiTarget(
    vercel_project_ref="vercel:project:example-app",
    project_id="prj_example",
    project_name="example-app",
    team_id="team_example",
    repository_ref=REPOSITORY_REF,
    github_repo_id=12345,
    production_branch="main",
)


class VercelHappyTransport:
    def __init__(self, *, existing: bool = False) -> None:
        self.existing = existing
        self.create_posts = 0

    @staticmethod
    def _deployment(state: str = "READY") -> dict[str, object]:
        return {
            "id": "dpl_preview_1",
            "name": "example-app",
            "target": "preview",
            "readyState": state,
            "url": "example-app-run-1.vercel.app" if state == "READY" else None,
            "project": {"id": "prj_example", "name": "example-app"},
            "gitSource": {
                "type": "github",
                "repoId": 12345,
                "ref": "parallax/run-1",
                "sha": COMMIT,
            },
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-only-vercel-scoped-token"
        path = request.url.path
        if request.method == "GET" and path == "/v9/projects/prj_example":
            return httpx.Response(
                200,
                json={
                    "id": "prj_example",
                    "name": "example-app",
                    "link": {"type": "github", "repoId": 12345},
                },
            )
        if request.method == "GET" and path == "/v6/deployments":
            return httpx.Response(
                200,
                json={"deployments": [{"uid": "dpl_preview_1"}] if self.existing else []},
            )
        if request.method == "POST" and path == "/v13/deployments":
            self.create_posts += 1
            body = _request_json(request)
            assert body == {
                "name": "example-app",
                "project": "prj_example",
                "target": "preview",
                "gitSource": {
                    "type": "github",
                    "repoId": 12345,
                    "ref": "parallax/run-1",
                    "sha": COMMIT,
                },
            }
            return httpx.Response(200, json=self._deployment("QUEUED"))
        if request.method == "GET" and path == "/v13/deployments/dpl_preview_1":
            return httpx.Response(200, json=self._deployment("READY"))
        raise AssertionError(f"unexpected Vercel request: {request.method} {request.url}")


def test_vercel_concrete_client_is_preview_only_and_reuses_exact_preview() -> None:
    handler = VercelHappyTransport(existing=False)
    client: VercelProviderClient = VercelPreviewRestClient(
        VercelCredentials(),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(handler),
    )

    created = client.create_preview(
        TARGET.vercel_project_ref,
        REPOSITORY_REF,
        COMMIT,
        "parallax/run-1",
        LINEAGE,
    )
    assert created.status is VercelPreviewStatus.QUEUED
    assert created.source_revision == COMMIT
    assert handler.create_posts == 1
    read_back = client.read_preview(TARGET.vercel_project_ref, "dpl_preview_1")
    assert read_back.status is VercelPreviewStatus.READY
    assert read_back.url == "https://example-app-run-1.vercel.app"

    replay_handler = VercelHappyTransport(existing=True)
    replay_client = VercelPreviewRestClient(
        VercelCredentials(),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(replay_handler),
    )
    replay = replay_client.create_preview(
        TARGET.vercel_project_ref,
        REPOSITORY_REF,
        COMMIT,
        "parallax/run-1",
        LINEAGE,
    )
    assert replay.deployment_id == "dpl_preview_1"
    assert replay_handler.create_posts == 0
