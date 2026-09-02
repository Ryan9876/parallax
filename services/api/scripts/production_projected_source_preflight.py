from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


_ENV_TARGETS = "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON"
_ENV_OIDC = "VERCEL_OIDC_TOKEN"
_MAX_TARGETS = 64
_MAX_TREE_ENTRIES = 1024
_MAX_FILE_BYTES = 256_000
_MAX_LINEAGE_FILES = 2_000
_MAX_LINEAGE_BYTES = 64_000_000
_GITHUB_API_VERSION = "2026-03-10"
_REPOSITORY = re.compile(r"^github:([^/\s]+)/([^/\s]+)$")
_CONNECTOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_SOURCE_PATH = re.compile(r"^[A-Za-z0-9._-](?:[A-Za-z0-9._/ -]{0,238}[A-Za-z0-9._-])?$")
_ALLOWED_BLOB_MODES = frozenset({"100644", "100755"})
_REQUIRED_READ_PERMISSIONS = ("contents:read", "metadata:read")
_PROVIDER_SECRET_PARTS = frozenset({".env", ".env.local", ".env.production", "secrets", "credentials"})
_LINEAGE_SECRET_FILENAMES = frozenset(
    {"credentials", "credentials.json", "secrets", "secrets.json", "id_rsa", "id_ed25519"}
)
_LINEAGE_SECRET_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx"})
_MAX_RATE_LIMIT_RETRY_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class Target:
    repository_ref: str
    github_connector: str
    production_branch: str

    @property
    def repository(self) -> tuple[str, str]:
        match = _REPOSITORY.fullmatch(self.repository_ref)
        if match is None:
            raise RuntimeError("invalid registered repository identity")
        return match.group(1), match.group(2)


def _targets() -> tuple[Target, ...]:
    raw = os.getenv(_ENV_TARGETS)
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("production provider target registry is unavailable")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("production provider target registry is invalid JSON") from exc
    if not isinstance(payload, list) or not 1 <= len(payload) <= _MAX_TARGETS:
        raise RuntimeError("production provider target registry must be bounded and non-empty")
    targets: list[Target] = []
    for raw_target in payload:
        if not isinstance(raw_target, dict):
            raise RuntimeError("production provider target registry contains an invalid target")
        repository_ref = raw_target.get("repository_ref")
        connector = raw_target.get("github_connector")
        branch = raw_target.get("production_branch")
        if not isinstance(repository_ref, str) or not _REPOSITORY.fullmatch(repository_ref):
            raise RuntimeError("production provider target has invalid repository identity")
        if not isinstance(connector, str) or not _CONNECTOR.fullmatch(connector):
            raise RuntimeError("production provider target has invalid Connect identity")
        if not isinstance(branch, str) or not branch or len(branch) > 255:
            raise RuntimeError("production provider target has invalid branch identity")
        targets.append(Target(repository_ref, connector, branch))
    return tuple(targets)


def _bounded_http_error(exc: HTTPError) -> str:
    try:
        raw = exc.read(4096).decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except Exception:
        return f"HTTP {exc.code}"
    if not isinstance(payload, dict):
        return f"HTTP {exc.code}"
    details: list[str] = []
    for key in ("code", "message", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            details.append(value[:160])
        elif isinstance(value, dict):
            for nested in ("code", "message"):
                nested_value = value.get(nested)
                if isinstance(nested_value, str) and nested_value:
                    details.append(nested_value[:160])
    return f"HTTP {exc.code}" + (f": {' | '.join(details[:2])}" if details else "")


def _github_rate_limit_retry_delay(exc: HTTPError, *, attempt: int) -> float | None:
    if exc.code != 403:
        return None
    remaining = str(exc.headers.get("X-RateLimit-Remaining") or "").strip()
    retry_after = str(exc.headers.get("Retry-After") or "").strip()
    if remaining != "0" and not retry_after:
        return None
    if retry_after:
        try:
            delay = float(retry_after)
        except ValueError:
            delay = float(attempt)
    else:
        reset = str(exc.headers.get("X-RateLimit-Reset") or "").strip()
        try:
            delay = max(0.0, float(reset) - time.time()) if reset else float(attempt)
        except ValueError:
            delay = float(attempt)
    return min(max(delay, 0.0), _MAX_RATE_LIMIT_RETRY_SECONDS)


def _json_request(request: Request, *, label: str) -> object:
    last_error = "provider request failed"
    for attempt in range(1, 4):
        retry_delay: float | None = None
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read()
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{label} returned invalid JSON") from exc
        except HTTPError as exc:
            retry_delay = _github_rate_limit_retry_delay(exc, attempt=attempt)
            last_error = _bounded_http_error(exc)
            if retry_delay is None and exc.code != 429 and not 500 <= exc.code <= 599:
                raise RuntimeError(f"{label} failed: {last_error}") from exc
        except (TimeoutError, URLError) as exc:
            last_error = "network unavailable"
            if attempt == 3:
                raise RuntimeError(f"{label} failed: {last_error}") from exc
        if attempt < 3:
            time.sleep(retry_delay if retry_delay is not None else float(attempt))
    raise RuntimeError(f"{label} failed after bounded retries: {last_error}")


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
        "User-Agent": "Parallax-Projected-Source-Preflight",
    }


def _authorization_details(repository: str) -> list[dict[str, object]]:
    return [
        {
            "type": "github_app_installation",
            "repositories": [repository],
            "permissions": list(_REQUIRED_READ_PERMISSIONS),
        }
    ]


def _connect_token(connector: str, repository: str, *, oidc: str) -> str:
    payload = _json_request(
        Request(
            f"https://api.vercel.com/v1/connect/token/{quote(connector, safe='')}",
            method="POST",
            data=json.dumps(
                {
                    "subject": {"type": "app"},
                    "authorizationDetails": _authorization_details(repository),
                }
            ).encode(),
            headers={"Authorization": f"Bearer {oidc}", "Content-Type": "application/json"},
        ),
        label="Vercel Connect projected-source preflight",
    )
    token = payload.get("token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Vercel Connect projected-source preflight returned no provider token")
    return token.strip()


def _lineage_secret_sensitive(path: str) -> bool:
    parts = tuple(part.casefold() for part in path.split("/"))
    filename = parts[-1] if parts else ""
    return (
        not parts
        or ".git" in parts
        or ".ssh" in parts
        or filename.startswith(".env")
        or filename in _LINEAGE_SECRET_FILENAMES
        or any(filename.endswith(suffix) for suffix in _LINEAGE_SECRET_SUFFIXES)
    )


def _provider_path_valid(path: str) -> bool:
    if not _SOURCE_PATH.fullmatch(path) or path.startswith("/"):
        return False
    parts = path.split("/")
    if ".." in parts:
        return False
    return not ({part.casefold() for part in parts} & _PROVIDER_SECRET_PARTS)


def _projected_entries(tree_payload: object) -> list[tuple[str, int]]:
    if not isinstance(tree_payload, dict) or tree_payload.get("truncated") is True:
        raise RuntimeError("projected-source tree is invalid or truncated")
    raw_entries = tree_payload.get("tree")
    if not isinstance(raw_entries, list) or len(raw_entries) > _MAX_TREE_ENTRIES:
        raise RuntimeError("projected-source tree exceeds the protected entry bound")
    projected: list[tuple[str, int]] = []
    for raw in raw_entries:
        if not isinstance(raw, dict) or raw.get("type") != "blob" or raw.get("mode") not in _ALLOWED_BLOB_MODES:
            continue
        path = raw.get("path")
        size = raw.get("size")
        if not isinstance(path, str) or not isinstance(size, int) or isinstance(size, bool):
            raise RuntimeError("projected-source tree contains an invalid file entry")
        if not 0 <= size <= _MAX_FILE_BYTES:
            raise RuntimeError(f"projected-source file exceeds byte bound: {path[:240]}")
        if _lineage_secret_sensitive(path):
            continue
        if not _provider_path_valid(path):
            raise RuntimeError(f"projection/provider path-policy mismatch: {path[:240]}")
        projected.append((path, size))
    if not projected:
        raise RuntimeError("projected-source tree contains no lineage-eligible files")
    if len(projected) > _MAX_LINEAGE_FILES:
        raise RuntimeError("projected-source file count exceeds durable lineage bound")
    if sum(size for _, size in projected) > _MAX_LINEAGE_BYTES:
        raise RuntimeError("projected-source aggregate bytes exceed durable lineage bound")
    return sorted(projected)


def _validate_contents_payload(payload: object, *, expected_path: str, expected_size: int) -> int:
    if not isinstance(payload, dict):
        raise RuntimeError(f"projected source response is invalid: {expected_path[:240]}")
    if payload.get("type") != "file" or payload.get("encoding") != "base64":
        raise RuntimeError(f"projected source is not base64 file content: {expected_path[:240]}")
    if payload.get("path") != expected_path:
        raise RuntimeError(f"projected source path mismatch: {expected_path[:240]}")
    size = payload.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size != expected_size or not 0 <= size <= _MAX_FILE_BYTES:
        raise RuntimeError(f"projected source size mismatch: {expected_path[:240]}")
    encoded = payload.get("content")
    if not isinstance(encoded, str):
        raise RuntimeError(f"projected source content is unavailable: {expected_path[:240]}")
    try:
        content = base64.b64decode("".join(encoded.split()), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError(f"projected source base64 is invalid: {expected_path[:240]}") from exc
    if len(content) != size:
        raise RuntimeError(f"projected source decoded size mismatch: {expected_path[:240]}")
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"projected source is not strict UTF-8: {expected_path[:240]}") from exc
    if "\x00" in text:
        raise RuntimeError(f"projected source contains NUL content: {expected_path[:240]}")
    digest = hashlib.sha256(content).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError(f"projected source digest is invalid: {expected_path[:240]}")
    return size


def _preflight_target(target: Target, *, oidc: str) -> tuple[int, int]:
    owner, repository = target.repository
    exact_repository = f"{owner}/{repository}"
    token = _connect_token(target.github_connector, exact_repository, oidc=oidc)
    headers = _headers(token)
    scope = _json_request(
        Request("https://api.github.com/installation/repositories?per_page=2", headers=headers),
        label="GitHub projected-source scoped installation preflight",
    )
    repositories = scope.get("repositories") if isinstance(scope, dict) else None
    if (
        not isinstance(scope, dict)
        or scope.get("total_count") != 1
        or not isinstance(repositories, list)
        or len(repositories) != 1
    ):
        raise RuntimeError("GitHub projected-source credential is not exactly one repository")
    scoped_repository = repositories[0]
    full_name = scoped_repository.get("full_name") if isinstance(scoped_repository, dict) else None
    if not isinstance(full_name, str) or full_name.casefold() != exact_repository.casefold():
        raise RuntimeError("GitHub projected-source credential does not match registered repository")
    encoded_owner = quote(owner, safe="")
    encoded_repository = quote(repository, safe="")
    branch_payload = _json_request(
        Request(
            f"https://api.github.com/repos/{encoded_owner}/{encoded_repository}/branches/{quote(target.production_branch, safe='')}",
            headers=headers,
        ),
        label="GitHub projected-source branch preflight",
    )
    commit = branch_payload.get("commit") if isinstance(branch_payload, dict) else None
    revision = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise RuntimeError("GitHub projected-source branch did not resolve to a commit")
    tree_payload = _json_request(
        Request(
            f"https://api.github.com/repos/{encoded_owner}/{encoded_repository}/git/trees/{quote(revision, safe='')}?recursive=1",
            headers=headers,
        ),
        label="GitHub projected-source tree preflight",
    )
    entries = _projected_entries(tree_payload)
    total = 0
    for path, size in entries:
        endpoint = (
            f"https://api.github.com/repos/{encoded_owner}/{encoded_repository}/contents/"
            f"{quote(path, safe='/')}?ref={quote(revision, safe='')}"
        )
        payload = _json_request(
            Request(endpoint, headers=headers),
            label=f"GitHub projected source read [{path[:180]}]",
        )
        total += _validate_contents_payload(payload, expected_path=path, expected_size=size)
    return len(entries), total


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production projected-source preflight: SKIP "
            f"(VERCEL_ENV={environment}; GitHub Connect authority remains production-only)"
        )
        return
    oidc = os.getenv(_ENV_OIDC)
    if not isinstance(oidc, str) or not oidc.strip():
        raise RuntimeError("production Vercel OIDC credential is unavailable")
    total_files = 0
    total_bytes = 0
    targets = _targets()
    for target in targets:
        files, size = _preflight_target(target, oidc=oidc.strip())
        total_files += files
        total_bytes += size
    print(
        "Production projected-source preflight: PASS "
        f"({len(targets)} target(s); {total_files} lineage-eligible files; {total_bytes} UTF-8 bytes)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production projected-source preflight: FAIL — {exc}", file=sys.stderr)
        raise
