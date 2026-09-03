from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from parallax_api.tools.providers.common import AcceptedSourceLineage, ProviderClientError
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
UPDATED_TREE = "4" * 40
UPDATED_BLOB = "5" * 40
CANONICAL_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MISSING_TREE = "8" * 40
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
        if request.method == "GET" and path in {
            f"/repos/acme/example-app/git/trees/{BASE}",
            f"/repos/acme/example-app/git/trees/{COMMIT}",
            f"/repos/acme/example-app/git/trees/{TREE}",
            f"/repos/acme/example-app/git/trees/{UPDATED_TREE}",
        }:
            is_commit = path.endswith(COMMIT) or path.endswith(UPDATED_TREE)
            content = b"print('updated')\n" if is_commit else b"print('hello')\n"
            return httpx.Response(
                200,
                json={
                    "sha": UPDATED_TREE if is_commit else TREE,
                    "truncated": False,
                    "tree": [
                        {"path": "src", "mode": "040000", "type": "tree", "sha": "6" * 40 if is_commit else TREE},
                        {
                            "path": "src/app.py",
                            "mode": "100644",
                            "type": "blob",
                            "sha": UPDATED_BLOB if is_commit else BLOB,
                            "size": len(content),
                        },
                    ],
                },
            )
        if request.method == "GET" and path == "/repos/acme/example-app/contents/src/app.py":
            content = (
                b"print('updated')\n"
                if request.url.params.get("ref") == COMMIT
                else b"print('hello')\n"
            )
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
            return httpx.Response(201, json={"sha": UPDATED_TREE})
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
                    "tree": {"sha": UPDATED_TREE},
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
    def __init__(
        self,
        *,
        existing: bool = False,
        response_target: object = None,
        include_target: bool = True,
    ) -> None:
        self.existing = existing
        self.response_target = response_target
        self.include_target = include_target
        self.create_posts = 0

    def _deployment(self, state: str = "READY") -> dict[str, object]:
        payload: dict[str, object] = {
            "id": "dpl_preview_1",
            "name": "example-app",
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
        if self.include_target:
            payload["target"] = self.response_target
        return payload

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
            assert request.url.params["projectId"] == "prj_example"
            assert request.url.params["branch"] == "parallax/run-1"
            assert request.url.params["sha"] == COMMIT
            assert "target" not in request.url.params
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
                "gitSource": {
                    "type": "github",
                    "repoId": 12345,
                    "ref": "parallax/run-1",
                    "sha": COMMIT,
                },
            }
            assert "target" not in body
            # Current create responses are not required to echo repository/source
            # identity. The client must validate those fields via full read-back.
            return httpx.Response(200, json={"id": "dpl_preview_1", "readyState": "QUEUED"})
        if request.method == "GET" and path == "/v13/deployments/dpl_preview_1":
            return httpx.Response(200, json=self._deployment("READY"))
        raise AssertionError(f"unexpected Vercel request: {request.method} {request.url}")


def _vercel_client(handler: VercelHappyTransport) -> VercelPreviewRestClient:
    return VercelPreviewRestClient(
        VercelCredentials(),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(handler),
    )


def test_vercel_concrete_client_is_preview_only_and_reuses_exact_preview() -> None:
    handler = VercelHappyTransport(existing=False)
    client: VercelProviderClient = _vercel_client(handler)

    created = client.create_preview(
        TARGET.vercel_project_ref,
        REPOSITORY_REF,
        COMMIT,
        "parallax/run-1",
        LINEAGE,
    )
    assert created.status is VercelPreviewStatus.READY
    assert created.source_revision == COMMIT
    assert handler.create_posts == 1
    read_back = client.read_preview(TARGET.vercel_project_ref, "dpl_preview_1")
    assert read_back.status is VercelPreviewStatus.READY
    assert read_back.url == "https://example-app-run-1.vercel.app"

    replay_handler = VercelHappyTransport(existing=True)
    replay_client = _vercel_client(replay_handler)
    replay = replay_client.create_preview(
        TARGET.vercel_project_ref,
        REPOSITORY_REF,
        COMMIT,
        "parallax/run-1",
        LINEAGE,
    )
    assert replay.deployment_id == "dpl_preview_1"
    assert replay_handler.create_posts == 0


@pytest.mark.parametrize("provider_target", ["production", "staging", "custom-preview-name"])
def test_vercel_create_rejects_every_non_null_deployment_target(provider_target: str) -> None:
    handler = VercelHappyTransport(response_target=provider_target)
    client = _vercel_client(handler)

    with pytest.raises(ProviderClientError, match="PRODUCTION_SCOPE_FORBIDDEN"):
        client.create_preview(
            TARGET.vercel_project_ref,
            REPOSITORY_REF,
            COMMIT,
            "parallax/run-1",
            LINEAGE,
        )
    assert handler.create_posts == 1


def test_vercel_preview_response_requires_explicit_null_target() -> None:
    handler = VercelHappyTransport(include_target=False)
    client = _vercel_client(handler)

    with pytest.raises(ProviderClientError, match="PROVIDER_INVALID_RESPONSE"):
        client.create_preview(
            TARGET.vercel_project_ref,
            REPOSITORY_REF,
            COMMIT,
            "parallax/run-1",
            LINEAGE,
        )
    assert handler.create_posts == 1


def test_vercel_replay_rejects_existing_non_preview_deployment() -> None:
    handler = VercelHappyTransport(existing=True, response_target="production")
    client = _vercel_client(handler)

    with pytest.raises(ProviderClientError, match="PRODUCTION_SCOPE_FORBIDDEN"):
        client.create_preview(
            TARGET.vercel_project_ref,
            REPOSITORY_REF,
            COMMIT,
            "parallax/run-1",
            LINEAGE,
        )
    assert handler.create_posts == 0


OTHER_HEAD = "9" * 40


class GitHubStaleRefTransport(GitHubHappyTransport):
    def __init__(
        self,
        *,
        stale_after_patch_reads: int = 1,
        unexpected_after_patch: bool = False,
    ) -> None:
        super().__init__()
        self.branch_ref_reads = 0
        self.stale_after_patch_reads = stale_after_patch_reads
        self.unexpected_after_patch = unexpected_after_patch

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        branch_path = "/repos/acme/example-app/git/ref/heads/parallax/run-1"
        if request.method == "GET" and path == branch_path:
            self.branch_ref_reads += 1
            if self.branch_ref_reads == 2:
                # GitHub acknowledged branch creation but the exact ref is not
                # visible to the immediately following commit-stage read.
                return httpx.Response(404, json={"message": "not found"})
            if self.branch_ref_reads >= 3:
                if self.unexpected_after_patch and self.branch_ref_reads == 3:
                    return httpx.Response(200, json=self._ref(OTHER_HEAD, "parallax/run-1"))
                if self.branch_ref_reads < 3 + self.stale_after_patch_reads:
                    # GitHub acknowledged the non-force PATCH but this read
                    # still returns the exact prior branch head.
                    return httpx.Response(200, json=self._ref(BASE, "parallax/run-1"))
        return super().__call__(request)


def _commit_file() -> GitHubCommitFile:
    content = "print('updated')\n"
    return GitHubCommitFile(
        "src/app.py",
        content,
        __import__("hashlib").sha256(content.encode()).hexdigest(),
    )


def test_github_ref_mutation_acknowledgements_bridge_only_immediate_stale_reads() -> None:
    handler = GitHubStaleRefTransport(stale_after_patch_reads=2)
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    assert client.resolve_repository(REPOSITORY_REF).head_revision == BASE
    assert client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE).head_revision == BASE
    commit = client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (_commit_file(),),
    )
    assert commit.commit_revision == COMMIT

    created = client.create_pull_request(
        REPOSITORY_REF,
        "parallax/run-1",
        COMMIT,
        "main",
        "Parallax change",
        "bounded body",
    )
    assert created.number == 42

    # The acknowledgement was consumed by the first stale read. A second
    # identical stale provider view cannot inherit or replay that authority.
    with pytest.raises(ProviderClientError, match="STALE_HEAD"):
        client.create_pull_request(
            REPOSITORY_REF,
            "parallax/run-1",
            COMMIT,
            "main",
            "Parallax change",
            "bounded body",
        )


def test_github_ref_mutation_acknowledgement_never_masks_unexpected_head() -> None:
    handler = GitHubStaleRefTransport(unexpected_after_patch=True)
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    assert client.resolve_repository(REPOSITORY_REF).head_revision == BASE
    client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE)
    client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (_commit_file(),),
    )

    with pytest.raises(ProviderClientError, match="STALE_HEAD"):
        client.create_pull_request(
            REPOSITORY_REF,
            "parallax/run-1",
            COMMIT,
            "main",
            "Parallax change",
            "bounded body",
        )
    assert handler.pull_posts == 0


def test_github_ref_mutation_acknowledgements_do_not_cross_repository_resolution() -> None:
    handler = GitHubStaleRefTransport(stale_after_patch_reads=2)
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    client.resolve_repository(REPOSITORY_REF)
    client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE)
    # A fresh repository resolution is the delivery-sequence boundary and
    # discards the one-shot branch-create acknowledgement.
    client.resolve_repository(REPOSITORY_REF)
    with pytest.raises(ProviderClientError, match="BRANCH_NOT_FOUND"):
        client.commit_files(
            REPOSITORY_REF,
            "parallax/run-1",
            BASE,
            LINEAGE,
            (_commit_file(),),
        )



class GitHubForgedReplayTransport(GitHubHappyTransport):
    def __init__(self) -> None:
        super().__init__()
        self.branch_head = COMMIT

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if (
            request.method == "GET"
            and request.url.path == f"/repos/acme/example-app/git/trees/{UPDATED_TREE}"
        ):
            return httpx.Response(
                200,
                json={
                    "sha": UPDATED_TREE,
                    "truncated": False,
                    "tree": [
                        {"path": "src", "mode": "040000", "type": "tree", "sha": "6" * 40},
                        {
                            "path": "src/app.py",
                            "mode": "100644",
                            "type": "blob",
                            "sha": UPDATED_BLOB,
                            "size": len(b"print('updated')\\n"),
                        },
                        {
                            "path": "src/extra.py",
                            "mode": "100644",
                            "type": "blob",
                            "sha": "7" * 40,
                            "size": 5,
                        },
                    ],
                },
            )
        return super().__call__(request)


def test_github_lineage_replay_rejects_same_message_parent_with_extra_tree_delta() -> None:
    handler = GitHubForgedReplayTransport()
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )
    client.resolve_repository(REPOSITORY_REF)

    with pytest.raises(ProviderClientError, match="STALE_PARENT"):
        client.commit_files(
            REPOSITORY_REF,
            "parallax/run-1",
            BASE,
            LINEAGE,
            (_commit_file(),),
        )
    assert handler.commit_posts == 0



class GitHubExactReplayTreeIdentityTransport(GitHubHappyTransport):
    def __init__(self) -> None:
        super().__init__()
        self.branch_head = COMMIT
        self.commit_sha_tree_reads: list[str] = []
        self.tree_sha_reads: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path in {
            f"/repos/acme/example-app/git/trees/{BASE}",
            f"/repos/acme/example-app/git/trees/{COMMIT}",
        }:
            self.commit_sha_tree_reads.append(path)
            return httpx.Response(404, json={"message": "tree object not found"})
        if request.method == "GET" and path in {
            f"/repos/acme/example-app/git/trees/{TREE}",
            f"/repos/acme/example-app/git/trees/{UPDATED_TREE}",
        }:
            self.tree_sha_reads.append(path)
        return super().__call__(request)


def test_github_exact_lineage_replay_resolves_commit_tree_identities() -> None:
    handler = GitHubExactReplayTreeIdentityTransport()
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )
    client.resolve_repository(REPOSITORY_REF)

    replay = client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (_commit_file(),),
    )

    assert replay.commit_revision == COMMIT
    assert handler.commit_posts == 0
    assert handler.commit_sha_tree_reads == []
    assert handler.tree_sha_reads == [
        f"/repos/acme/example-app/git/trees/{TREE}",
        f"/repos/acme/example-app/git/trees/{UPDATED_TREE}",
    ]


class GitHubMalformedReplayTreeIdentityTransport(GitHubHappyTransport):
    def __init__(self) -> None:
        super().__init__()
        self.branch_head = COMMIT
        self.tree_reads = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == f"/repos/acme/example-app/git/commits/{COMMIT}":
            return httpx.Response(
                200,
                json={
                    "sha": COMMIT,
                    "message": GitHubRestProviderClient._lineage_message(LINEAGE),
                    "tree": {},
                    "parents": [{"sha": BASE}],
                },
            )
        if request.method == "GET" and "/git/trees/" in path:
            self.tree_reads += 1
        return super().__call__(request)


def test_github_exact_lineage_replay_rejects_malformed_commit_tree_identity() -> None:
    handler = GitHubMalformedReplayTreeIdentityTransport()
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )
    client.resolve_repository(REPOSITORY_REF)

    with pytest.raises(ProviderClientError, match="PROVIDER_INVALID_RESPONSE"):
        client.commit_files(
            REPOSITORY_REF,
            "parallax/run-1",
            BASE,
            LINEAGE,
            (_commit_file(),),
        )

    assert handler.commit_posts == 0
    assert handler.tree_reads == 0



class GitHubCanonicalEmptyParentReplayTransport(GitHubHappyTransport):
    def __init__(self) -> None:
        super().__init__()
        self.branch_head = COMMIT
        self.empty_tree_reads = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == f"/repos/acme/example-app/git/commits/{BASE}":
            return httpx.Response(
                200,
                json={
                    "sha": BASE,
                    "message": "base",
                    "tree": {"sha": CANONICAL_EMPTY_TREE},
                    "parents": [],
                },
            )
        if request.method == "GET" and path == f"/repos/acme/example-app/git/trees/{CANONICAL_EMPTY_TREE}":
            self.empty_tree_reads += 1
            return httpx.Response(404, json={"message": "canonical empty tree not materialized"})
        return super().__call__(request)


def test_github_exact_lineage_replay_uses_canonical_empty_parent_without_tree_get() -> None:
    handler = GitHubCanonicalEmptyParentReplayTransport()
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )
    client.resolve_repository(REPOSITORY_REF)

    replay = client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (_commit_file(),),
    )

    assert replay.commit_revision == COMMIT
    assert handler.commit_posts == 0
    assert handler.empty_tree_reads == 0


class GitHubMissingNonCanonicalParentTreeTransport(GitHubHappyTransport):
    def __init__(self) -> None:
        super().__init__()
        self.branch_head = COMMIT
        self.missing_tree_reads = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == f"/repos/acme/example-app/git/commits/{BASE}":
            return httpx.Response(
                200,
                json={
                    "sha": BASE,
                    "message": "base",
                    "tree": {"sha": MISSING_TREE},
                    "parents": [],
                },
            )
        if request.method == "GET" and path == f"/repos/acme/example-app/git/trees/{MISSING_TREE}":
            self.missing_tree_reads += 1
            return httpx.Response(404, json={"message": "missing tree"})
        return super().__call__(request)


def test_github_exact_lineage_replay_does_not_normalize_noncanonical_missing_tree() -> None:
    handler = GitHubMissingNonCanonicalParentTreeTransport()
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )
    client.resolve_repository(REPOSITORY_REF)

    with pytest.raises(ProviderClientError, match="SOURCE_NOT_FOUND"):
        client.commit_files(
            REPOSITORY_REF,
            "parallax/run-1",
            BASE,
            LINEAGE,
            (_commit_file(),),
        )

    assert handler.commit_posts == 0
    assert handler.missing_tree_reads == 1
