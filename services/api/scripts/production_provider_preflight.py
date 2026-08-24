from __future__ import annotations

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
_GITHUB_API_VERSION = "2026-03-10"
_GITHUB_CONNECTOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_VERCEL_TOKEN_ENV = re.compile(r"^PARALLAX_VERCEL_TOKEN_[A-Z0-9_]{1,96}$")
_REPOSITORY = re.compile(r"^github:([^/\s]+)/([^/\s]+)$")


@dataclass(frozen=True, slots=True)
class Target:
    repository_ref: str
    github_connector: str
    github_repo_id: int
    production_branch: str
    vercel_token_env: str

    @classmethod
    def from_json(cls, value: object) -> "Target":
        if not isinstance(value, dict):
            raise RuntimeError("provider target registry contains a non-object entry")
        repository_ref = value.get("repository_ref")
        github_connector = value.get("github_connector")
        github_repo_id = value.get("github_repo_id")
        production_branch = value.get("production_branch")
        vercel_token_env = value.get("vercel_token_env")
        if not isinstance(repository_ref, str) or not _REPOSITORY.fullmatch(repository_ref):
            raise RuntimeError("provider target has invalid GitHub repository identity")
        if not isinstance(github_connector, str) or not _GITHUB_CONNECTOR.fullmatch(github_connector):
            raise RuntimeError("provider target has invalid Vercel Connect identity")
        if not isinstance(github_repo_id, int) or isinstance(github_repo_id, bool) or github_repo_id <= 0:
            raise RuntimeError("provider target has invalid GitHub repository id")
        if (
            not isinstance(production_branch, str)
            or production_branch != production_branch.strip()
            or not production_branch
            or len(production_branch) > 255
        ):
            raise RuntimeError("provider target has invalid production branch")
        if not isinstance(vercel_token_env, str) or not _VERCEL_TOKEN_ENV.fullmatch(vercel_token_env):
            raise RuntimeError("provider target has invalid Vercel credential reference")
        return cls(
            repository_ref=repository_ref,
            github_connector=github_connector,
            github_repo_id=github_repo_id,
            production_branch=production_branch,
            vercel_token_env=vercel_token_env,
        )

    @property
    def repository(self) -> tuple[str, str]:
        match = _REPOSITORY.fullmatch(self.repository_ref)
        if match is None:  # defensive; construction already validated this
            raise RuntimeError("provider target has invalid GitHub repository identity")
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
    targets = tuple(Target.from_json(item) for item in payload)
    keys = [item.repository_ref.casefold() for item in targets]
    if len(keys) != len(set(keys)):
        raise RuntimeError("production provider target registry contains duplicate repositories")
    return targets


def _bounded_http_error(exc: HTTPError) -> str:
    try:
        raw = exc.read(4096).decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except Exception:
        return f"HTTP {exc.code}"
    if not isinstance(payload, dict):
        return f"HTTP {exc.code}"
    candidates: list[str] = []
    for key in ("code", "message", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            candidates.append(value[:200])
        elif isinstance(value, dict):
            for nested in ("code", "message"):
                nested_value = value.get(nested)
                if isinstance(nested_value, str) and nested_value:
                    candidates.append(nested_value[:200])
    detail = " | ".join(candidates[:3])
    return f"HTTP {exc.code}" + (f": {detail}" if detail else "")


def _json_request(request: Request, *, label: str) -> object:
    last_error = "provider request failed"
    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read()
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{label} returned invalid JSON") from exc
        except HTTPError as exc:
            last_error = _bounded_http_error(exc)
            if exc.code != 429 and not 500 <= exc.code <= 599:
                raise RuntimeError(f"{label} failed: {last_error}") from exc
        except (TimeoutError, URLError) as exc:
            last_error = "network unavailable"
            if attempt == 3:
                raise RuntimeError(f"{label} failed: {last_error}") from exc
        if attempt < 3:
            time.sleep(float(attempt))
    raise RuntimeError(f"{label} failed after bounded retries: {last_error}")


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
        "User-Agent": "Parallax-Production-Provider-Preflight",
    }


def _connect_token(target: Target, *, oidc: str) -> str:
    connector = quote(target.github_connector, safe="")
    payload = _json_request(
        Request(
            f"https://api.vercel.com/v1/connect/token/{connector}",
            method="POST",
            data=json.dumps({"subject": {"type": "app"}}).encode(),
            headers={
                "Authorization": f"Bearer {oidc}",
                "Content-Type": "application/json",
            },
        ),
        label="Vercel Connect credential preflight",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Vercel Connect credential preflight returned invalid payload")
    token = payload.get("token")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Vercel Connect credential preflight returned no provider token")
    return token.strip()


def _preflight_target(target: Target, *, oidc: str) -> None:
    vercel_token = os.getenv(target.vercel_token_env)
    if not isinstance(vercel_token, str) or not vercel_token.strip():
        raise RuntimeError("registered Vercel Preview credential is unavailable")

    owner, repository = target.repository
    provider_token = _connect_token(target, oidc=oidc)
    github_headers = _github_headers(provider_token)

    scope = _json_request(
        Request("https://api.github.com/installation/repositories?per_page=2", headers=github_headers),
        label="GitHub installation-scope preflight",
    )
    if not isinstance(scope, dict):
        raise RuntimeError("GitHub installation-scope preflight returned invalid payload")
    repositories = scope.get("repositories")
    if scope.get("total_count") != 1 or not isinstance(repositories, list) or len(repositories) != 1:
        raise RuntimeError("GitHub installation scope is not exactly one repository")
    full_name = repositories[0].get("full_name") if isinstance(repositories[0], dict) else None
    expected_name = f"{owner}/{repository}"
    if not isinstance(full_name, str) or full_name.casefold() != expected_name.casefold():
        raise RuntimeError("GitHub installation scope does not match registered repository")

    encoded_owner = quote(owner, safe="")
    encoded_repository = quote(repository, safe="")
    repository_payload = _json_request(
        Request(
            f"https://api.github.com/repos/{encoded_owner}/{encoded_repository}",
            headers=github_headers,
        ),
        label="GitHub repository identity preflight",
    )
    if not isinstance(repository_payload, dict) or repository_payload.get("id") != target.github_repo_id:
        raise RuntimeError("GitHub repository numeric identity mismatch")

    encoded_branch = quote(target.production_branch, safe="")
    branch_payload = _json_request(
        Request(
            f"https://api.github.com/repos/{encoded_owner}/{encoded_repository}/branches/{encoded_branch}",
            headers=github_headers,
        ),
        label="GitHub production-branch preflight",
    )
    commit = branch_payload.get("commit") if isinstance(branch_payload, dict) else None
    revision = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise RuntimeError("GitHub production branch did not resolve to a commit")


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production provider preflight: SKIP "
            f"(VERCEL_ENV={environment}; GitHub Connect authority remains production-only)"
        )
        return

    oidc = os.getenv(_ENV_OIDC)
    if not isinstance(oidc, str) or not oidc.strip():
        raise RuntimeError("production Vercel OIDC credential is unavailable")

    targets = _targets()
    for target in targets:
        _preflight_target(target, oidc=oidc.strip())
    print(f"Production provider preflight: PASS ({len(targets)} registered target(s))")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production provider preflight: FAIL — {exc}", file=sys.stderr)
        raise
