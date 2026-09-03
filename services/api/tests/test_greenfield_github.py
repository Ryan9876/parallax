from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from parallax_api.code.greenfield_github import GreenfieldGitHubClient
from parallax_api.tools.providers import ProviderClientError
from parallax_api.tools.providers.credentials import ProviderCredentialKind, ScopedBearerCredential
from parallax_api.tools.providers.github_client import GitHubRestProviderClient


REPOSITORY = "github:Ryan9876/empty-target"
DEFAULT_BRANCH = "main"
BOOTSTRAP = "a" * 40
BASELINE = "b" * 40
BLOB = "c" * 40
BOOTSTRAP_TREE = "e" * 40
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
OTHER = "9" * 40
PROVENANCE = "d" * 64
CONTENT = f"parallax-greenfield-v1\nprovenance={PROVENANCE}\n"
ACTOR = {
    "name": "Parallax App Builder",
    "email": "parallax-app-builder@users.noreply.github.com",
    "date": "2000-01-01T00:00:00Z",
}


class _Credentials:
    def credential_for_repository(self, repository_ref: str) -> ScopedBearerCredential:
        assert repository_ref == REPOSITORY
        return ScopedBearerCredential(
            provider="github",
            resource_ref=repository_ref,
            kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
            secret="greenfield-test-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )


def _client(handler) -> GreenfieldGitHubClient:
    delegate = GitHubRestProviderClient(_Credentials(), transport=httpx.MockTransport(handler))
    return GreenfieldGitHubClient(delegate)


def _repo() -> httpx.Response:
    return httpx.Response(
        200,
        json={"full_name": "Ryan9876/empty-target", "default_branch": DEFAULT_BRANCH},
    )


def _commit(message: str, parents: list[dict[str, str]], tree_sha: str) -> dict[str, object]:
    return {
        "message": message,
        "parents": parents,
        "tree": {"sha": tree_sha},
        "author": ACTOR,
        "committer": ACTOR,
    }


def _bootstrap_tree() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "truncated": False,
            "tree": [
                {
                    "path": ".parallax-greenfield",
                    "type": "blob",
                    "mode": "100644",
                    "sha": BLOB,
                }
            ],
        },
    )


def _empty_tree() -> httpx.Response:
    return httpx.Response(200, json={"sha": EMPTY_TREE, "truncated": False, "tree": []})


def test_positive_empty_inspection_is_distinct_from_not_found() -> None:
    def empty(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(404, json={"message": "Not Found"})
        raise AssertionError(request.url)

    result = _client(empty).inspect_repository(REPOSITORY)
    assert result.is_empty is True
    assert result.head_revision is None
    assert result.default_branch == DEFAULT_BRANCH

    def missing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    with pytest.raises(ProviderClientError, match="REPOSITORY_NOT_FOUND"):
        _client(missing).inspect_repository(REPOSITORY)


def test_real_github_empty_ref_409_is_narrowly_normalized() -> None:
    def empty_409(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(409, json={"message": "Git Repository is empty."})
        raise AssertionError(request.url)

    result = _client(empty_409).inspect_repository(REPOSITORY)
    assert result.is_empty is True
    assert result.head_revision is None

    def unrelated_409(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(409, json={"message": "Reference conflict"})
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="PROVIDER_CONFLICT"):
        _client(unrelated_409).inspect_repository(REPOSITORY)

    def malformed_409(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(409, text="not-json")
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="PROVIDER_INVALID_RESPONSE"):
        _client(malformed_409).inspect_repository(REPOSITORY)


def test_initializer_uses_contents_root_then_git_data_empty_cleanup_without_contents_delete() -> None:
    mutations: list[str] = []
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main") and request.method == "GET":
            ref_reads += 1
            if ref_reads == 1:
                return httpx.Response(409, json={"message": "Git Repository is empty."})
            if ref_reads in {2, 3}:
                return httpx.Response(200, json={"object": {"sha": BOOTSTRAP}})
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith("/contents/.parallax-greenfield") and request.method == "PUT":
            mutations.append("contents-put")
            payload = json.loads(request.content)
            assert base64.b64decode(payload["content"]).decode() == CONTENT
            assert payload["branch"] == DEFAULT_BRANCH
            assert payload["author"] == ACTOR == payload["committer"]
            return httpx.Response(201, json={"commit": {"sha": BOOTSTRAP}, "content": {"sha": BLOB}})
        if path.endswith("/contents/.parallax-greenfield") and request.method == "DELETE":
            raise AssertionError("provider-realistic last-file cleanup must not use Contents DELETE")
        if path.endswith(f"/git/commits/{BOOTSTRAP}") and request.method == "GET":
            return httpx.Response(200, json=_commit("Initialize Parallax greenfield baseline", [], BOOTSTRAP_TREE))
        if path.endswith(f"/git/trees/{BOOTSTRAP_TREE}") and request.method == "GET":
            return _bootstrap_tree()
        if path.endswith(f"/git/blobs/{BLOB}") and request.method == "GET":
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(CONTENT.encode()).decode()})
        if path.endswith("/git/trees") and request.method == "POST":
            mutations.append("tree-create")
            payload = json.loads(request.content)
            assert payload == {
                "base_tree": BOOTSTRAP_TREE,
                "tree": [{"path": ".parallax-greenfield", "mode": "100644", "type": "blob", "sha": None}],
            }
            return httpx.Response(201, json={"sha": EMPTY_TREE})
        if path.endswith(f"/git/trees/{EMPTY_TREE}") and request.method == "GET":
            return _empty_tree()
        if path.endswith("/git/commits") and request.method == "POST":
            mutations.append("commit-create")
            payload = json.loads(request.content)
            assert payload == {
                "message": "Finalize Parallax empty greenfield baseline",
                "tree": EMPTY_TREE,
                "parents": [BOOTSTRAP],
                "author": ACTOR,
                "committer": ACTOR,
            }
            return httpx.Response(201, json={"sha": BASELINE})
        if path.endswith(f"/git/commits/{BASELINE}") and request.method == "GET":
            return httpx.Response(200, json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}], EMPTY_TREE))
        if path.endswith("/git/refs/heads/main") and request.method == "PATCH":
            mutations.append("ref-update")
            payload = json.loads(request.content)
            assert payload == {"sha": BASELINE, "force": False}
            return httpx.Response(200, json={"ref": "refs/heads/main", "object": {"sha": BASELINE}})
        raise AssertionError((request.method, request.url))

    result = _client(handler).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert mutations == ["contents-put", "tree-create", "commit-create", "ref-update"]
    assert result.initialized is True
    assert result.baseline_revision == BASELINE
    assert result.bootstrap_revision == BOOTSTRAP


def test_initializer_fails_closed_when_default_ref_moves_before_non_force_update() -> None:
    ref_reads = 0
    patched = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads, patched
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main") and request.method == "GET":
            ref_reads += 1
            if ref_reads == 1:
                return httpx.Response(409, json={"message": "Git Repository is empty."})
            if ref_reads == 2:
                return httpx.Response(200, json={"object": {"sha": BOOTSTRAP}})
            return httpx.Response(200, json={"object": {"sha": OTHER}})
        if path.endswith("/contents/.parallax-greenfield") and request.method == "PUT":
            return httpx.Response(201, json={"commit": {"sha": BOOTSTRAP}, "content": {"sha": BLOB}})
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            return httpx.Response(200, json=_commit("Initialize Parallax greenfield baseline", [], BOOTSTRAP_TREE))
        if path.endswith(f"/git/trees/{BOOTSTRAP_TREE}"):
            return _bootstrap_tree()
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(CONTENT.encode()).decode()})
        if path.endswith("/git/trees") and request.method == "POST":
            return httpx.Response(201, json={"sha": EMPTY_TREE})
        if path.endswith(f"/git/trees/{EMPTY_TREE}"):
            return _empty_tree()
        if path.endswith("/git/commits") and request.method == "POST":
            return httpx.Response(201, json={"sha": BASELINE})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(200, json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}], EMPTY_TREE))
        if request.method == "PATCH":
            patched = True
            raise AssertionError("ref drift must fail before PATCH")
        raise AssertionError((request.method, request.url))

    with pytest.raises(ProviderClientError, match="GREENFIELD_INITIALIZATION_CONFLICT"):
        _client(handler).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert patched is False


def test_initializer_rejects_nonempty_cleanup_tree_before_commit_or_ref_mutation() -> None:
    ref_reads = 0
    later_mutation = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads, later_mutation
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main") and request.method == "GET":
            ref_reads += 1
            if ref_reads == 1:
                return httpx.Response(409, json={"message": "Git Repository is empty."})
            return httpx.Response(200, json={"object": {"sha": BOOTSTRAP}})
        if path.endswith("/contents/.parallax-greenfield") and request.method == "PUT":
            return httpx.Response(201, json={"commit": {"sha": BOOTSTRAP}, "content": {"sha": BLOB}})
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            return httpx.Response(200, json=_commit("Initialize Parallax greenfield baseline", [], BOOTSTRAP_TREE))
        if path.endswith(f"/git/trees/{BOOTSTRAP_TREE}"):
            return _bootstrap_tree()
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(CONTENT.encode()).decode()})
        if path.endswith("/git/trees") and request.method == "POST":
            return httpx.Response(201, json={"sha": EMPTY_TREE})
        if path.endswith(f"/git/trees/{EMPTY_TREE}"):
            return httpx.Response(200, json={"truncated": False, "tree": [{"path": "unexpected.txt"}]})
        if request.method in {"POST", "PATCH"}:
            later_mutation = True
        raise AssertionError((request.method, request.url))

    with pytest.raises(ProviderClientError, match="GREENFIELD_BASELINE_MISMATCH"):
        _client(handler).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert later_mutation is False


def test_existing_exact_baseline_is_replayed_read_only_and_conflict_fails_closed() -> None:
    methods: list[str] = []

    def exact(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(200, json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}], EMPTY_TREE))
        if path.endswith(f"/git/trees/{EMPTY_TREE}"):
            return _empty_tree()
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            return httpx.Response(200, json=_commit("Initialize Parallax greenfield baseline", [], BOOTSTRAP_TREE))
        if path.endswith(f"/git/trees/{BOOTSTRAP_TREE}"):
            return _bootstrap_tree()
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(CONTENT.encode()).decode()})
        raise AssertionError(request.url)

    replay = _client(exact).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert replay.initialized is False
    assert set(methods) == {"GET"}

    def conflict(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(200, json=_commit("unrelated user commit", [{"sha": BOOTSTRAP}], EMPTY_TREE))
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="GREENFIELD_BASELINE_MISMATCH"):
        _client(conflict).initialize_empty_baseline(REPOSITORY, PROVENANCE)



def test_actor_verification_accepts_provider_owned_offset_aware_timestamps() -> None:
    payload = _commit("message", [], EMPTY_TREE)
    payload["author"] = {**ACTOR, "date": "2026-09-02T04:01:00Z"}
    payload["committer"] = {**ACTOR, "date": "2026-09-02T00:01:01-04:00"}

    GreenfieldGitHubClient._verify_actor(payload)


@pytest.mark.parametrize("field", ["author", "committer"])
@pytest.mark.parametrize(
    ("identity_key", "wrong_value"),
    [
        ("name", "Other Builder"),
        ("email", "other@example.com"),
    ],
)
def test_actor_verification_rejects_identity_drift(
    field: str,
    identity_key: str,
    wrong_value: str,
) -> None:
    payload = _commit("message", [], EMPTY_TREE)
    payload["author"] = {**ACTOR, "date": "2026-09-02T04:01:00Z"}
    payload["committer"] = {**ACTOR, "date": "2026-09-02T04:01:01+00:00"}
    payload[field] = {**payload[field], identity_key: wrong_value}

    with pytest.raises(ProviderClientError, match="GREENFIELD_BASELINE_MISMATCH"):
        GreenfieldGitHubClient._verify_actor(payload)


@pytest.mark.parametrize(
    "bad_date",
    [None, "", 1234, "not-a-timestamp", "2026-09-02T04:01:00"],
)
@pytest.mark.parametrize("field", ["author", "committer"])
def test_actor_verification_rejects_missing_malformed_or_naive_timestamp(
    field: str,
    bad_date: object,
) -> None:
    payload = _commit("message", [], EMPTY_TREE)
    payload["author"] = {**ACTOR, "date": "2026-09-02T04:01:00Z"}
    payload["committer"] = {**ACTOR, "date": "2026-09-02T04:01:01+00:00"}
    if bad_date is None:
        payload[field].pop("date")
    else:
        payload[field]["date"] = bad_date

    with pytest.raises(ProviderClientError, match="GREENFIELD_BASELINE_MISMATCH"):
        GreenfieldGitHubClient._verify_actor(payload)


def test_existing_baseline_with_provider_timestamps_replays_get_only() -> None:
    methods: list[str] = []

    def provider_commit(
        message: str,
        parents: list[dict[str, str]],
        tree_sha: str,
        author_date: str,
        committer_date: str,
    ) -> dict[str, object]:
        payload = _commit(message, parents, tree_sha)
        payload["author"] = {**ACTOR, "date": author_date}
        payload["committer"] = {**ACTOR, "date": committer_date}
        return payload

    def exact(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(
                200,
                json=provider_commit(
                    "Finalize Parallax empty greenfield baseline",
                    [{"sha": BOOTSTRAP}],
                    EMPTY_TREE,
                    "2026-09-02T04:01:01Z",
                    "2026-09-02T04:01:01+00:00",
                ),
            )
        if path.endswith(f"/git/trees/{EMPTY_TREE}"):
            return _empty_tree()
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            return httpx.Response(
                200,
                json=provider_commit(
                    "Initialize Parallax greenfield baseline",
                    [],
                    BOOTSTRAP_TREE,
                    "2026-09-02T04:01:00Z",
                    "2026-09-02T00:01:00-04:00",
                ),
            )
        if path.endswith(f"/git/trees/{BOOTSTRAP_TREE}"):
            return _bootstrap_tree()
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(
                200,
                json={
                    "encoding": "base64",
                    "content": base64.b64encode(CONTENT.encode()).decode(),
                },
            )
        raise AssertionError(request.url)

    replay = _client(exact).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert replay.initialized is False
    assert replay.baseline_revision == BASELINE
    assert replay.bootstrap_revision == BOOTSTRAP
    assert set(methods) == {"GET"}



def test_existing_canonical_empty_tree_replay_omits_provider_tree_get() -> None:
    methods: list[str] = []
    requested_paths: list[str] = []

    def exact(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        path = request.url.path
        requested_paths.append(path)
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            payload = _commit(
                "Finalize Parallax empty greenfield baseline",
                [{"sha": BOOTSTRAP}],
                EMPTY_TREE,
            )
            payload["author"] = {**ACTOR, "date": "2026-09-02T04:01:01Z"}
            payload["committer"] = {**ACTOR, "date": "2026-09-02T00:01:01-04:00"}
            return httpx.Response(200, json=payload)
        if path.endswith(f"/git/trees/{EMPTY_TREE}"):
            raise AssertionError("canonical empty tree must not require provider Trees GET during replay")
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            payload = _commit(
                "Initialize Parallax greenfield baseline",
                [],
                BOOTSTRAP_TREE,
            )
            payload["author"] = {**ACTOR, "date": "2026-09-02T04:01:00Z"}
            payload["committer"] = {**ACTOR, "date": "2026-09-02T00:01:00-04:00"}
            return httpx.Response(200, json=payload)
        if path.endswith(f"/git/trees/{BOOTSTRAP_TREE}"):
            return _bootstrap_tree()
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(
                200,
                json={
                    "encoding": "base64",
                    "content": base64.b64encode(CONTENT.encode()).decode(),
                },
            )
        raise AssertionError(request.url)

    replay = _client(exact).initialize_empty_baseline(REPOSITORY, PROVENANCE)

    assert replay.initialized is False
    assert replay.baseline_revision == BASELINE
    assert replay.bootstrap_revision == BOOTSTRAP
    assert set(methods) == {"GET"}
    assert not any(path.endswith(f"/git/trees/{EMPTY_TREE}") for path in requested_paths)


def test_existing_baseline_rejects_noncanonical_cleanup_tree_without_normalizing_missing_tree() -> None:
    noncanonical_tree = OTHER
    tree_reads = 0

    def mismatch(request: httpx.Request) -> httpx.Response:
        nonlocal tree_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(
                200,
                json=_commit(
                    "Finalize Parallax empty greenfield baseline",
                    [{"sha": BOOTSTRAP}],
                    noncanonical_tree,
                ),
            )
        if path.endswith(f"/git/trees/{noncanonical_tree}"):
            tree_reads += 1
            return httpx.Response(404, json={"message": "Not Found"})
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="GREENFIELD_BASELINE_MISMATCH"):
        _client(mismatch).initialize_empty_baseline(REPOSITORY, PROVENANCE)

    assert tree_reads == 0



def test_commit_bearing_empty_inspection_is_stable_and_exact() -> None:
    head = "f" * 40
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            ref_reads += 1
            return httpx.Response(200, json={"object": {"sha": head}})
        if path.endswith(f"/git/commits/{head}"):
            return httpx.Response(
                200,
                json={"message": "Ordinary empty commit", "parents": [{"sha": OTHER}], "tree": {"sha": EMPTY_TREE}},
            )
        raise AssertionError((request.method, request.url))

    result = _client(handler).inspect_repository(REPOSITORY)
    assert ref_reads == 2
    assert result.is_empty is False
    assert result.is_commit_bearing_empty is True
    assert result.is_canonical_baseline_candidate is False
    assert result.head_revision == head
    assert result.head_tree_revision == EMPTY_TREE
    assert result.head_message == "Ordinary empty commit"


def test_canonical_cleanup_message_is_preserved_as_strict_baseline_candidate() -> None:
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            ref_reads += 1
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(
                200,
                json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}], EMPTY_TREE),
            )
        raise AssertionError((request.method, request.url))

    result = _client(handler).inspect_repository(REPOSITORY)
    assert ref_reads == 2
    assert result.is_commit_bearing_empty is True
    assert result.is_canonical_baseline_candidate is True


def test_commit_bearing_inspection_fails_closed_when_default_ref_moves() -> None:
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            ref_reads += 1
            revision = BASELINE if ref_reads == 1 else OTHER
            return httpx.Response(200, json={"object": {"sha": revision}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(
                200,
                json={"message": "Ordinary empty commit", "parents": [], "tree": {"sha": EMPTY_TREE}},
            )
        raise AssertionError((request.method, request.url))

    with pytest.raises(ProviderClientError, match="GREENFIELD_INITIALIZATION_CONFLICT"):
        _client(handler).inspect_repository(REPOSITORY)


def test_commit_bearing_nonempty_inspection_remains_distinct() -> None:
    head = "f" * 40

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": head}})
        if path.endswith(f"/git/commits/{head}"):
            return httpx.Response(
                200,
                json={"message": "Repository now has source", "parents": [], "tree": {"sha": OTHER}},
            )
        raise AssertionError((request.method, request.url))

    result = _client(handler).inspect_repository(REPOSITORY)
    assert result.is_empty is False
    assert result.is_commit_bearing_empty is False
    assert result.head_tree_revision == OTHER
