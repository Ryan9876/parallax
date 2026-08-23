from __future__ import annotations

import base64
import binascii
from hashlib import sha256
from typing import Any
from urllib.parse import quote

import httpx

from .common import AcceptedSourceLineage, ProviderClientError, require_repository_ref
from .credentials import GitHubCredentialProvider, require_scoped_credential
from .github import (
    GitHubBranchResult,
    GitHubCommitFile,
    GitHubCommitResult,
    GitHubFileResult,
    GitHubProviderClient,
    GitHubPullRequestResult,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
)


_GITHUB_API = "https://api.github.com"
_GITHUB_API_VERSION = "2022-11-28"
_COMMIT_ACTOR = {
    "name": "Parallax App Builder",
    "email": "parallax-app-builder@users.noreply.github.com",
    "date": "2000-01-01T00:00:00Z",
}
_ALLOWED_BLOB_MODES = frozenset({"100644", "100755"})
_ALLOWED_TREE_MODE = "040000"


def _repository_parts(repository_ref: str) -> tuple[str, str]:
    require_repository_ref(repository_ref)
    owner, repository = repository_ref.removeprefix("github:").split("/", 1)
    return owner, repository


def _dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    return value


def _list(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    return value


def _string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    return value


class GitHubRestProviderClient(GitHubProviderClient):
    """Concrete fixed-surface GitHub REST client for the accepted #62 Protocol."""

    def __init__(
        self,
        credential_provider: GitHubCredentialProvider,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 60:
            raise ValueError("GitHub timeout must be between 0 and 60 seconds")
        self._credential_provider = credential_provider
        self._http = httpx.Client(
            base_url=_GITHUB_API,
            transport=transport,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )

    def _headers(self, repository_ref: str) -> dict[str, str]:
        try:
            credential = self._credential_provider.credential_for_repository(repository_ref)
        except ProviderClientError:
            raise
        except Exception as exc:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from exc
        credential = require_scoped_credential(
            credential,
            provider="github",
            resource_ref=repository_ref,
        )
        return {
            "Authorization": credential.authorization_value(),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _GITHUB_API_VERSION,
            "User-Agent": "Parallax-App-Builder",
        }

    def _send(
        self,
        method: str,
        repository_ref: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        try:
            return self._http.request(
                method,
                path,
                headers=self._headers(repository_ref),
                params=params,
                json=json,
            )
        except ProviderClientError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderClientError("PROVIDER_TIMEOUT") from exc
        except httpx.RequestError as exc:
            raise ProviderClientError("PROVIDER_UNAVAILABLE") from exc
        except Exception as exc:
            raise ProviderClientError("PROVIDER_ERROR") from exc

    @staticmethod
    def _raise_status(
        response: httpx.Response,
        *,
        not_found: str = "PROVIDER_NOT_FOUND",
        conflict: str = "PROVIDER_CONFLICT",
    ) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        if status == 404:
            raise ProviderClientError(not_found)
        if status in {401, 403}:
            if response.headers.get("x-ratelimit-remaining") == "0" or response.headers.get("retry-after"):
                raise ProviderClientError("PROVIDER_RATE_LIMITED")
            raise ProviderClientError("PROVIDER_AUTH_DENIED")
        if status == 429:
            raise ProviderClientError("PROVIDER_RATE_LIMITED")
        if status in {409, 422}:
            raise ProviderClientError(conflict)
        if status in {400, 405}:
            raise ProviderClientError("PROVIDER_INVALID_REQUEST")
        if 500 <= status <= 599:
            raise ProviderClientError("PROVIDER_UNAVAILABLE")
        raise ProviderClientError("PROVIDER_ERROR")

    @staticmethod
    def _json(response: httpx.Response) -> object:
        try:
            return response.json()
        except Exception as exc:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc

    @staticmethod
    def _repo_path(repository_ref: str) -> str:
        owner, repository = _repository_parts(repository_ref)
        return f"/repos/{quote(owner, safe='')}/{quote(repository, safe='')}"

    def _get_ref(self, repository_ref: str, branch_name: str) -> str | None:
        path = f"{self._repo_path(repository_ref)}/git/ref/heads/{quote(branch_name, safe='/')}"
        response = self._send("GET", repository_ref, path)
        if response.status_code == 404:
            return None
        self._raise_status(response)
        payload = _dict(self._json(response))
        object_payload = _dict(payload.get("object"))
        return _string(object_payload.get("sha"))

    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState:
        owner, repository = _repository_parts(repository_ref)
        response = self._send("GET", repository_ref, self._repo_path(repository_ref))
        self._raise_status(response, not_found="REPOSITORY_NOT_FOUND")
        payload = _dict(self._json(response))
        full_name = _string(payload.get("full_name"))
        if full_name.casefold() != f"{owner}/{repository}".casefold():
            raise ProviderClientError("REPOSITORY_MISMATCH")
        default_branch = _string(payload.get("default_branch"))
        head = self._get_ref(repository_ref, default_branch)
        if head is None:
            raise ProviderClientError("SOURCE_NOT_FOUND")
        return GitHubRepositoryState(repository_ref, default_branch, head)

    def read_tree(
        self,
        repository_ref: str,
        source_revision: str,
        *,
        max_entries: int,
    ) -> GitHubTreeResult:
        _repository_parts(repository_ref)
        if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        path = f"{self._repo_path(repository_ref)}/git/trees/{quote(source_revision, safe='')}"
        response = self._send("GET", repository_ref, path, params={"recursive": "1"})
        self._raise_status(response, not_found="SOURCE_NOT_FOUND")
        payload = _dict(self._json(response))
        if payload.get("truncated") is True:
            raise ProviderClientError("SOURCE_TREE_TRUNCATED")
        raw_entries = _list(payload.get("tree"))
        if len(raw_entries) > max_entries:
            raise ProviderClientError("SOURCE_TREE_TOO_LARGE")

        entries: list[GitHubTreeEntry] = []
        for raw in raw_entries:
            item = _dict(raw)
            path_value = _string(item.get("path"))
            object_revision = _string(item.get("sha"))
            entry_type = item.get("type")
            mode = item.get("mode")
            if entry_type == "tree" and mode == _ALLOWED_TREE_MODE:
                entries.append(GitHubTreeEntry(path_value, "tree", 0, object_revision))
                continue
            if entry_type == "blob" and mode in _ALLOWED_BLOB_MODES:
                size = item.get("size")
                if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                    raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
                entries.append(GitHubTreeEntry(path_value, "file", size, object_revision))
                continue
            raise ProviderClientError("UNSUPPORTED_SOURCE_ENTRY")

        return GitHubTreeResult(repository_ref, source_revision, tuple(entries))

    def read_file(
        self,
        repository_ref: str,
        source_revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> GitHubFileResult:
        _repository_parts(repository_ref)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
            raise ValueError("max_bytes must be a positive integer")
        endpoint = f"{self._repo_path(repository_ref)}/contents/{quote(path, safe='/')}"
        response = self._send("GET", repository_ref, endpoint, params={"ref": source_revision})
        self._raise_status(response, not_found="SOURCE_NOT_FOUND")
        payload = _dict(self._json(response))
        if payload.get("type") != "file" or payload.get("encoding") != "base64":
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT")
        returned_path = _string(payload.get("path"))
        if returned_path != path:
            raise ProviderClientError("SOURCE_MISMATCH")
        size = payload.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or not 0 <= size <= max_bytes:
            raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
        encoded = payload.get("content")
        if not isinstance(encoded, str):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        try:
            content_bytes = base64.b64decode("".join(encoded.split()), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc
        if len(content_bytes) != size or len(content_bytes) > max_bytes:
            raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
        try:
            content = content_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT") from exc
        return GitHubFileResult(
            repository_ref,
            source_revision,
            path,
            content,
            sha256(content_bytes).hexdigest(),
        )

    def create_branch(
        self,
        repository_ref: str,
        branch_name: str,
        base_revision: str,
    ) -> GitHubBranchResult:
        _repository_parts(repository_ref)
        current = self._get_ref(repository_ref, branch_name)
        if current is not None:
            if current != base_revision:
                raise ProviderClientError("BRANCH_CONFLICT")
            return GitHubBranchResult(repository_ref, branch_name, base_revision, current)

        response = self._send(
            "POST",
            repository_ref,
            f"{self._repo_path(repository_ref)}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_revision},
        )
        if response.status_code in {409, 422}:
            replay = self._get_ref(repository_ref, branch_name)
            if replay == base_revision:
                return GitHubBranchResult(repository_ref, branch_name, base_revision, replay)
            raise ProviderClientError("BRANCH_CONFLICT")
        self._raise_status(response, conflict="BRANCH_CONFLICT")
        payload = _dict(self._json(response))
        returned_ref = _string(payload.get("ref"))
        object_payload = _dict(payload.get("object"))
        head = _string(object_payload.get("sha"))
        if returned_ref != f"refs/heads/{branch_name}" or head != base_revision:
            raise ProviderClientError("SOURCE_MISMATCH")
        return GitHubBranchResult(repository_ref, branch_name, base_revision, head)

    @staticmethod
    def _lineage_message(lineage: AcceptedSourceLineage) -> str:
        return (
            "Parallax accepted source lineage\n\n"
            f"Parallax-Project: {lineage.project_id}\n"
            f"Parallax-Run: {lineage.run_id}\n"
            f"Parallax-Lineage: {lineage.lineage_id}\n"
            f"Parallax-Content-Digest: {lineage.content_digest}"
        )

    def _commit_payload(self, repository_ref: str, revision: str) -> dict[str, Any]:
        endpoint = f"{self._repo_path(repository_ref)}/git/commits/{quote(revision, safe='')}"
        response = self._send("GET", repository_ref, endpoint)
        self._raise_status(response, not_found="SOURCE_NOT_FOUND")
        return _dict(self._json(response))

    def _is_lineage_replay(
        self,
        repository_ref: str,
        revision: str,
        expected_parent_revision: str,
        lineage: AcceptedSourceLineage,
    ) -> bool:
        payload = self._commit_payload(repository_ref, revision)
        if payload.get("message") != self._lineage_message(lineage):
            return False
        parents = _list(payload.get("parents"))
        return (
            len(parents) == 1
            and isinstance(parents[0], dict)
            and parents[0].get("sha") == expected_parent_revision
        )

    def commit_files(
        self,
        repository_ref: str,
        branch_name: str,
        expected_parent_revision: str,
        lineage: AcceptedSourceLineage,
        files: tuple[GitHubCommitFile, ...],
    ) -> GitHubCommitResult:
        _repository_parts(repository_ref)
        current = self._get_ref(repository_ref, branch_name)
        if current is None:
            raise ProviderClientError("BRANCH_NOT_FOUND")
        if current != expected_parent_revision:
            if self._is_lineage_replay(
                repository_ref,
                current,
                expected_parent_revision,
                lineage,
            ):
                return GitHubCommitResult(
                    repository_ref,
                    branch_name,
                    expected_parent_revision,
                    current,
                    lineage.lineage_id,
                    lineage.content_digest,
                )
            raise ProviderClientError("STALE_PARENT")

        parent_payload = self._commit_payload(repository_ref, expected_parent_revision)
        parent_tree = _dict(parent_payload.get("tree"))
        base_tree = _string(parent_tree.get("sha"))
        tree_entries: list[dict[str, object]] = []
        for item in files:
            if not isinstance(item, GitHubCommitFile):
                raise TypeError("files must contain GitHubCommitFile values")
            tree_entries.append(
                {
                    "path": item.path,
                    "mode": "100644",
                    "type": "blob",
                    "content": item.content,
                }
            )

        tree_response = self._send(
            "POST",
            repository_ref,
            f"{self._repo_path(repository_ref)}/git/trees",
            json={"base_tree": base_tree, "tree": tree_entries},
        )
        self._raise_status(tree_response, conflict="STALE_PARENT")
        tree_payload = _dict(self._json(tree_response))
        tree_sha = _string(tree_payload.get("sha"))

        commit_response = self._send(
            "POST",
            repository_ref,
            f"{self._repo_path(repository_ref)}/git/commits",
            json={
                "message": self._lineage_message(lineage),
                "tree": tree_sha,
                "parents": [expected_parent_revision],
                "author": dict(_COMMIT_ACTOR),
                "committer": dict(_COMMIT_ACTOR),
            },
        )
        self._raise_status(commit_response, conflict="STALE_PARENT")
        commit_payload = _dict(self._json(commit_response))
        commit_revision = _string(commit_payload.get("sha"))

        ref_response = self._send(
            "PATCH",
            repository_ref,
            f"{self._repo_path(repository_ref)}/git/refs/heads/{quote(branch_name, safe='/')}",
            json={"sha": commit_revision, "force": False},
        )
        if ref_response.status_code in {409, 422}:
            final_head = self._get_ref(repository_ref, branch_name)
            if final_head != commit_revision:
                raise ProviderClientError("STALE_PARENT")
        else:
            self._raise_status(ref_response, conflict="STALE_PARENT")
            final_head = self._get_ref(repository_ref, branch_name)
            if final_head != commit_revision:
                raise ProviderClientError("SOURCE_MISMATCH")

        return GitHubCommitResult(
            repository_ref,
            branch_name,
            expected_parent_revision,
            commit_revision,
            lineage.lineage_id,
            lineage.content_digest,
        )

    def _parse_pull_request(
        self,
        repository_ref: str,
        payload: dict[str, Any],
    ) -> GitHubPullRequestResult:
        owner, repository = _repository_parts(repository_ref)
        number = payload.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        head = _dict(payload.get("head"))
        base = _dict(payload.get("base"))
        head_repo = _dict(head.get("repo"))
        base_repo = _dict(base.get("repo"))
        expected_name = f"{owner}/{repository}".casefold()
        if _string(head_repo.get("full_name")).casefold() != expected_name:
            raise ProviderClientError("REPOSITORY_MISMATCH")
        if _string(base_repo.get("full_name")).casefold() != expected_name:
            raise ProviderClientError("REPOSITORY_MISMATCH")
        state = _string(payload.get("state")).upper()
        return GitHubPullRequestResult(
            repository_ref,
            number,
            _string(head.get("ref")),
            _string(head.get("sha")),
            _string(base.get("ref")),
            state,
            _string(payload.get("html_url")),
        )

    def _find_pull_request(
        self,
        repository_ref: str,
        head_branch: str,
        expected_head_revision: str,
        base_branch: str,
    ) -> GitHubPullRequestResult | None:
        owner, _ = _repository_parts(repository_ref)
        response = self._send(
            "GET",
            repository_ref,
            f"{self._repo_path(repository_ref)}/pulls",
            params={
                "state": "open",
                "head": f"{owner}:{head_branch}",
                "base": base_branch,
                "per_page": 20,
            },
        )
        self._raise_status(response)
        payload = _list(self._json(response))
        for raw in payload:
            pull_request = self._parse_pull_request(repository_ref, _dict(raw))
            if pull_request.head_branch != head_branch or pull_request.base_branch != base_branch:
                continue
            if pull_request.head_revision != expected_head_revision:
                raise ProviderClientError("PULL_REQUEST_CONFLICT", result_identity=f"pr:{pull_request.number}")
            return pull_request
        return None

    def create_pull_request(
        self,
        repository_ref: str,
        head_branch: str,
        expected_head_revision: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> GitHubPullRequestResult:
        _repository_parts(repository_ref)
        current = self._get_ref(repository_ref, head_branch)
        if current is None:
            raise ProviderClientError("BRANCH_NOT_FOUND")
        if current != expected_head_revision:
            raise ProviderClientError("STALE_HEAD")
        existing = self._find_pull_request(
            repository_ref,
            head_branch,
            expected_head_revision,
            base_branch,
        )
        if existing is not None:
            return existing

        response = self._send(
            "POST",
            repository_ref,
            f"{self._repo_path(repository_ref)}/pulls",
            json={"title": title, "head": head_branch, "base": base_branch, "body": body},
        )
        if response.status_code == 422:
            replay = self._find_pull_request(
                repository_ref,
                head_branch,
                expected_head_revision,
                base_branch,
            )
            if replay is not None:
                return replay
            raise ProviderClientError("PULL_REQUEST_CONFLICT")
        self._raise_status(response, conflict="PULL_REQUEST_CONFLICT")
        pull_request = self._parse_pull_request(repository_ref, _dict(self._json(response)))
        if (
            pull_request.head_branch != head_branch
            or pull_request.head_revision != expected_head_revision
            or pull_request.base_branch != base_branch
        ):
            raise ProviderClientError("SOURCE_MISMATCH")
        return pull_request

    def read_pull_request(
        self,
        repository_ref: str,
        number: int,
    ) -> GitHubPullRequestResult:
        _repository_parts(repository_ref)
        response = self._send(
            "GET",
            repository_ref,
            f"{self._repo_path(repository_ref)}/pulls/{number}",
        )
        self._raise_status(response, not_found="PULL_REQUEST_NOT_FOUND")
        return self._parse_pull_request(repository_ref, _dict(self._json(response)))
