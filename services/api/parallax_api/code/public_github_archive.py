from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from io import BytesIO
import re
import tarfile
from urllib.parse import quote

import httpx

from ..tools.providers.common import ProviderClientError, require_repository_ref, require_source_revision
from ..tools.providers.github import (
    MAX_FILE_BYTES,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
)
from .production_source_projection import ProjectedGitHubFileResult, is_lineage_secret_sensitive_path


_GITHUB_WEB = "https://github.com"
_GITHUB_CODELOAD = "https://codeload.github.com"
_MAX_ARCHIVE_BYTES = 64_000_000
_MAX_ARCHIVE_MEMBERS = 4_096
_HEX_OBJECT = re.compile(r"^[0-9a-f]{40,64}$")
_DEFAULT_BRANCH = re.compile(r"^refs/heads/(?P<branch>[A-Za-z0-9][A-Za-z0-9._/-]{0,127})$")


@dataclass(frozen=True, slots=True)
class _PublicSourceSnapshot:
    repository_ref: str
    source_revision: str
    files: dict[str, bytes]


class PublicGitHubArchiveReadClient:
    """Read immutable public GitHub source without the anonymous REST quota.

    Repository visibility and the exact HEAD commit are established through the
    unauthenticated Git smart-HTTP upload-pack advertisement. Source bytes are
    then loaded from GitHub's commit-addressed codeload archive for that exact
    revision. No bearer credential, Vercel credential, GitHub REST request, or
    source mutation is available through this client.
    """

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
            raise TypeError("GitHub public-source timeout must be numeric")
        if not 0 < float(timeout_seconds) <= 60:
            raise ValueError("GitHub public-source timeout must be between 0 and 60 seconds")
        self._http = httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )
        self._snapshots: dict[tuple[str, str], _PublicSourceSnapshot] = {}

    @staticmethod
    def _parts(repository_ref: str) -> tuple[str, str]:
        require_repository_ref(repository_ref)
        owner, repository = repository_ref.removeprefix("github:").split("/", 1)
        return owner, repository

    @staticmethod
    def _headers(*, accept: str | None = None) -> dict[str, str]:
        result = {"User-Agent": "Parallax-App-Builder-Public-Source"}
        if accept is not None:
            result["Accept"] = accept
        return result

    @staticmethod
    def _raise_status(response: httpx.Response, *, not_found: str) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        if status in {401, 404}:
            raise ProviderClientError(not_found)
        if status == 403:
            if response.headers.get("x-ratelimit-remaining") == "0" or response.headers.get("retry-after"):
                raise ProviderClientError("PROVIDER_RATE_LIMITED")
            # GitHub intentionally hides inaccessible repositories from
            # unauthenticated callers. Preserve that non-disclosing boundary.
            raise ProviderClientError(not_found)
        if status == 429:
            raise ProviderClientError("PROVIDER_RATE_LIMITED")
        if 500 <= status <= 599:
            raise ProviderClientError("PROVIDER_UNAVAILABLE")
        raise ProviderClientError("PROVIDER_ERROR")

    def _get(self, url: str, *, accept: str | None = None) -> httpx.Response:
        try:
            return self._http.get(url, headers=self._headers(accept=accept))
        except httpx.TimeoutException as exc:
            raise ProviderClientError("PROVIDER_TIMEOUT") from exc
        except httpx.RequestError as exc:
            raise ProviderClientError("PROVIDER_UNAVAILABLE") from exc

    @staticmethod
    def _pkt_lines(payload: bytes) -> tuple[bytes, ...]:
        lines: list[bytes] = []
        offset = 0
        while offset < len(payload):
            if len(payload) - offset < 4:
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
            prefix = payload[offset : offset + 4]
            try:
                length = int(prefix, 16)
            except ValueError as exc:
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc
            offset += 4
            if length == 0:
                continue
            if length < 4:
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
            body_length = length - 4
            end = offset + body_length
            if end > len(payload):
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
            lines.append(payload[offset:end])
            offset = end
        return tuple(lines)

    @classmethod
    def _advertised_head(cls, payload: bytes) -> tuple[str, str]:
        head_revision: str | None = None
        default_branch: str | None = None
        for line in cls._pkt_lines(payload):
            if line.startswith(b"# service=") or line.startswith(b"version "):
                continue
            try:
                text = line.rstrip(b"\n").decode("ascii", errors="strict")
            except UnicodeDecodeError as exc:
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc
            reference, _, capabilities = text.partition("\x00")
            revision, separator, ref_name = reference.partition(" ")
            if separator != " " or not _HEX_OBJECT.fullmatch(revision):
                continue
            if ref_name == "HEAD":
                head_revision = revision
                for capability in capabilities.split(" "):
                    if not capability.startswith("symref=HEAD:"):
                        continue
                    match = _DEFAULT_BRANCH.fullmatch(capability.removeprefix("symref=HEAD:"))
                    if match is not None:
                        default_branch = match.group("branch")
                        break
        if head_revision is None or default_branch is None:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        require_source_revision(head_revision)
        require_source_revision(default_branch, field="default_branch")
        return head_revision, default_branch

    def _resolve_public_head(self, repository_ref: str) -> tuple[str, str]:
        owner, repository = self._parts(repository_ref)
        url = (
            f"{_GITHUB_WEB}/{quote(owner, safe='')}/{quote(repository, safe='')}.git/info/refs"
            "?service=git-upload-pack"
        )
        response = self._get(url, accept="application/x-git-upload-pack-advertisement")
        self._raise_status(response, not_found="REPOSITORY_NOT_FOUND")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type and content_type != "application/x-git-upload-pack-advertisement":
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        return self._advertised_head(response.content)

    def _archive_bytes(self, repository_ref: str, source_revision: str) -> bytes:
        owner, repository = self._parts(repository_ref)
        require_source_revision(source_revision)
        url = (
            f"{_GITHUB_CODELOAD}/{quote(owner, safe='')}/{quote(repository, safe='')}"
            f"/tar.gz/{quote(source_revision, safe='')}"
        )
        response = self._get(url, accept="application/gzip")
        self._raise_status(response, not_found="SOURCE_NOT_FOUND")
        declared = response.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > _MAX_ARCHIVE_BYTES:
                    raise ProviderClientError("SOURCE_TREE_TOO_LARGE")
            except ValueError as exc:
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc
        payload = response.content
        if len(payload) > _MAX_ARCHIVE_BYTES:
            raise ProviderClientError("SOURCE_TREE_TOO_LARGE")
        return payload

    @staticmethod
    def _relative_member_path(name: str, *, root: str | None) -> tuple[str | None, str | None]:
        normalized = name.rstrip("/")
        if not normalized:
            return root, None
        parts = normalized.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ProviderClientError("UNSUPPORTED_SOURCE_ENTRY")
        if root is None:
            root = parts[0]
        elif parts[0] != root:
            raise ProviderClientError("SOURCE_MISMATCH")
        if len(parts) == 1:
            return root, None
        relative = "/".join(parts[1:])
        return root, relative

    def _snapshot(self, repository_ref: str, source_revision: str) -> _PublicSourceSnapshot:
        key = (repository_ref, source_revision)
        cached = self._snapshots.get(key)
        if cached is not None:
            return cached

        archive = self._archive_bytes(repository_ref, source_revision)
        files: dict[str, bytes] = {}
        total_bytes = 0
        root: str | None = None
        try:
            with tarfile.open(fileobj=BytesIO(archive), mode="r:gz") as bundle:
                members = bundle.getmembers()
                if len(members) > _MAX_ARCHIVE_MEMBERS:
                    raise ProviderClientError("SOURCE_TREE_TOO_LARGE")
                for member in members:
                    root, path = self._relative_member_path(member.name, root=root)
                    if path is None or member.isdir():
                        continue
                    if not member.isfile() or member.issym() or member.islnk():
                        raise ProviderClientError("UNSUPPORTED_SOURCE_ENTRY")
                    if is_lineage_secret_sensitive_path(path):
                        continue
                    if member.size < 0 or member.size > MAX_FILE_BYTES:
                        raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
                    total_bytes += member.size
                    if total_bytes > _MAX_ARCHIVE_BYTES:
                        raise ProviderClientError("SOURCE_TREE_TOO_LARGE")
                    extracted = bundle.extractfile(member)
                    if extracted is None:
                        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
                    content = extracted.read(MAX_FILE_BYTES + 1)
                    if len(content) != member.size or len(content) > MAX_FILE_BYTES:
                        raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
                    if path in files:
                        raise ProviderClientError("SOURCE_MISMATCH")
                    files[path] = content
        except ProviderClientError:
            raise
        except (tarfile.TarError, OSError, EOFError) as exc:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc

        if root is None or not files:
            raise ProviderClientError("SOURCE_NOT_FOUND")
        snapshot = _PublicSourceSnapshot(
            repository_ref=repository_ref,
            source_revision=source_revision,
            files=files,
        )
        self._snapshots[key] = snapshot
        return snapshot

    @staticmethod
    def _blob_revision(content: bytes) -> str:
        header = f"blob {len(content)}\0".encode("ascii")
        return sha1(header + content).hexdigest()

    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState:
        head_revision, default_branch = self._resolve_public_head(repository_ref)
        # Prove the exact advertised revision is downloadable before accepting
        # public source authority. The cached snapshot is reused by tree/files.
        self._snapshot(repository_ref, head_revision)
        return GitHubRepositoryState(repository_ref, default_branch, head_revision)

    def read_tree(
        self,
        repository_ref: str,
        source_revision: str,
        *,
        max_entries: int,
    ) -> GitHubTreeResult:
        self._parts(repository_ref)
        require_source_revision(source_revision)
        if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        snapshot = self._snapshot(repository_ref, source_revision)
        if len(snapshot.files) > max_entries:
            raise ProviderClientError("SOURCE_TREE_TOO_LARGE")
        entries = tuple(
            GitHubTreeEntry(
                path=path,
                kind="file",
                size=len(content),
                object_revision=self._blob_revision(content),
            )
            for path, content in sorted(snapshot.files.items())
        )
        return GitHubTreeResult(repository_ref, source_revision, entries)

    def read_file(
        self,
        repository_ref: str,
        source_revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> ProjectedGitHubFileResult:
        self._parts(repository_ref)
        require_source_revision(source_revision)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
            raise ValueError("max_bytes must be a positive integer")
        if is_lineage_secret_sensitive_path(path):
            raise ProviderClientError("SOURCE_PATH_EXCLUDED")
        content = self._snapshot(repository_ref, source_revision).files.get(path)
        if content is None:
            raise ProviderClientError("SOURCE_NOT_FOUND")
        if len(content) > max_bytes:
            raise ProviderClientError("SOURCE_FILE_TOO_LARGE")
        try:
            text = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT") from exc
        if "\x00" in text:
            raise ProviderClientError("UNSUPPORTED_SOURCE_CONTENT")
        from hashlib import sha256

        return ProjectedGitHubFileResult(
            repository_ref=repository_ref,
            source_revision=source_revision,
            path=path,
            content=text,
            content_sha256=sha256(content).hexdigest(),
        )


__all__ = ["PublicGitHubArchiveReadClient"]
