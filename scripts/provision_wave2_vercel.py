from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TEAM_SLUG = "lew7"
API_PROJECT_ID = "prj_4lhve1AXZntfauaGHvkuaGWC6KJX"
API_PROJECT_NAME = "parallax-api"
PREVIEW_PROJECT_ID = "prj_wLXC5JjjetJf0H97kncRlqczD3OC"
PREVIEW_PROJECT_NAME = "parallax"
PREVIEW_PROJECT_REF = "vercel:preview:parallax"
REPOSITORY_REF = "github:Ryan9876/parallax"
GITHUB_REPO_ID = 1340272514
PRODUCTION_BRANCH = "main"
CONNECTOR = "github/parallax-runtime"
CONNECTOR_NAME = "parallax-runtime"
VERCEL_TOKEN_ENV = "PARALLAX_VERCEL_TOKEN_PARALLAX"
TARGET_REGISTRY_ENV = "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON"
BLOB_TOKEN_ENV = "BLOB_READ_WRITE_TOKEN"
BLOB_STORE_NAME = "parallax-source-lineage"


class ProvisioningError(RuntimeError):
    pass


def _redact(value: str, secrets: Iterable[str] = ()) -> str:
    result = value
    for secret in secrets:
        if secret:
            result = result.replace(secret, "<redacted>")
    return result


def _run(
    args: list[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    check: bool = True,
    secrets: Iterable[str] = (),
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    process = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and process.returncode != 0:
        command = " ".join(args[:3])
        detail = _redact((process.stderr or process.stdout).strip(), secrets)
        raise ProvisioningError(f"{command} failed: {detail or 'no diagnostic output'}")
    return process


def _json_token(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProvisioningError("Vercel token command did not return JSON") from exc

    def walk(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("token", "value", "secret"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.startswith(("vcp_", "vca_")):
                    return candidate
            for child in value.values():
                found = walk(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found:
                    return found
        return None

    token = walk(payload)
    if token is None:
        raise ProvisioningError("Vercel token JSON did not contain a plaintext access token")
    return token


def _env_keys(text: str) -> set[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    keys: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            key = value.get("key")
            if isinstance(key, str):
                keys.add(key)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    if payload is not None:
        walk(payload)
    if not keys:
        for line in text.splitlines():
            for candidate in (BLOB_TOKEN_ENV, VERCEL_TOKEN_ENV, TARGET_REGISTRY_ENV):
                if candidate in line:
                    keys.add(candidate)
    return keys


def target_registry_json() -> str:
    return json.dumps(
        [
            {
                "vercel_project_ref": PREVIEW_PROJECT_REF,
                "project_id": PREVIEW_PROJECT_ID,
                "project_name": PREVIEW_PROJECT_NAME,
                "team_id": "team_JgE8AWWz36uzRbeR6V6EWg9k",
                "repository_ref": REPOSITORY_REF,
                "github_repo_id": GITHUB_REPO_ID,
                "production_branch": PRODUCTION_BRANCH,
                "github_connector": CONNECTOR,
                "vercel_token_env": VERCEL_TOKEN_ENV,
            }
        ],
        sort_keys=True,
        separators=(",", ":"),
    )


def _env_list(repo: Path, environment: str) -> set[str]:
    result = _run(
        ["vercel", "env", "ls", environment, "--format=json"],
        cwd=repo,
    )
    return _env_keys(result.stdout)


def _set_env(repo: Path, name: str, value: str, environment: str, *, sensitive: bool) -> None:
    existing = _env_list(repo, environment)
    secret_values = (value,) if sensitive else ()
    if name in existing:
        _run(
            ["vercel", "env", "update", name, environment],
            cwd=repo,
            input_text=value + "\n",
            secrets=secret_values,
        )
    else:
        command = ["vercel", "env", "add", name, environment]
        if sensitive:
            command.append("--sensitive")
        _run(command, cwd=repo, input_text=value + "\n", secrets=secret_values)


def _verify_scoped_token(token: str) -> None:
    def status(project_id: str) -> int:
        request = Request(
            f"https://api.vercel.com/v9/projects/{project_id}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code)
        except URLError as exc:
            raise ProvisioningError("could not verify project-scoped Vercel token") from exc

    allowed = status(PREVIEW_PROJECT_ID)
    denied = status(API_PROJECT_ID)
    if not 200 <= allowed < 300:
        raise ProvisioningError("new Vercel token cannot access its registered Preview project")
    if 200 <= denied < 300:
        raise ProvisioningError("new Vercel token is broader than the registered Preview project")


def _ensure_link(repo: Path) -> None:
    _run(
        ["vercel", "link", "--yes", "--project", API_PROJECT_ID, "--scope", TEAM_SLUG],
        cwd=repo,
    )


def _ensure_blob(repo: Path) -> None:
    stores = _run(["vercel", "blob", "list-stores", "--all"], cwd=repo)
    if BLOB_STORE_NAME not in stores.stdout:
        _run(
            [
                "vercel",
                "blob",
                "create-store",
                BLOB_STORE_NAME,
                "--access",
                "private",
                "--region",
                "iad1",
                "--yes",
            ],
            cwd=repo,
        )
    for environment in ("preview", "production"):
        if BLOB_TOKEN_ENV not in _env_list(repo, environment):
            raise ProvisioningError(
                f"private Blob store exists but {BLOB_TOKEN_ENV} is not linked to {environment}"
            )


def _connector_present(repo: Path) -> bool:
    result = _run(["vercel", "connect", "list", "--format=json"], cwd=repo, check=False)
    text = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode == 0 and CONNECTOR in text


def _ensure_connector(repo: Path) -> None:
    if not _connector_present(repo):
        # GitHub installation consent can open a browser. This is the one expected
        # operator interaction in an otherwise automated provisioning pass.
        _run(
            [
                "vercel",
                "connect",
                "create",
                "github",
                "--name",
                CONNECTOR_NAME,
            ],
            cwd=repo,
        )
    if not _connector_present(repo):
        raise ProvisioningError(f"GitHub connector {CONNECTOR} was not created")
    for environment in ("preview", "production"):
        attached = _run(
            [
                "vercel",
                "connect",
                "attach",
                CONNECTOR,
                "--project",
                API_PROJECT_ID,
                "--environment",
                environment,
            ],
            cwd=repo,
            check=False,
        )
        if attached.returncode != 0:
            detail = ((attached.stderr or "") + "\n" + (attached.stdout or "")).lower()
            if "already" not in detail or not any(word in detail for word in ("attach", "link", "connected")):
                raise ProvisioningError(
                    f"could not attach {CONNECTOR} to {environment}: "
                    f"{_redact(detail.strip()) or 'no diagnostic output'}"
                )


def _create_preview_token(repo: Path) -> str:
    result = _run(
        [
            "vercel",
            "tokens",
            "add",
            "Parallax Wave 2 Preview target",
            "--project",
            PREVIEW_PROJECT_ID,
            "--format=json",
        ],
        cwd=repo,
    )
    token = _json_token(result.stdout)
    _verify_scoped_token(token)
    return token


def verify(repo: Path) -> None:
    for environment in ("preview", "production"):
        keys = _env_list(repo, environment)
        missing = {BLOB_TOKEN_ENV, VERCEL_TOKEN_ENV, TARGET_REGISTRY_ENV} - keys
        if missing:
            raise ProvisioningError(
                f"{environment} is missing required Vercel environment keys: {', '.join(sorted(missing))}"
            )
    if not _connector_present(repo):
        raise ProvisioningError(f"GitHub connector {CONNECTOR} is unavailable")


def provision(repo: Path) -> None:
    _ensure_link(repo)
    _ensure_blob(repo)
    _ensure_connector(repo)
    token = _create_preview_token(repo)
    try:
        registry = target_registry_json()
        for environment in ("preview", "production"):
            _set_env(repo, VERCEL_TOKEN_ENV, token, environment, sensitive=True)
            _set_env(repo, TARGET_REGISTRY_ENV, registry, environment, sensitive=False)
    finally:
        token = ""  # shorten lifetime of the plaintext reference
    verify(repo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Provision or verify the external Vercel prerequisites for the validated Wave 2 release. "
            "This command never applies database migrations, merges GitHub code, or deploys production."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--provision", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    parser.add_argument(
        "--api-dir",
        default="services/api",
        help="Path to the parallax-api Vercel project directory (default: services/api)",
    )
    args = parser.parse_args(argv)

    if shutil.which("vercel") is None:
        print("ERROR: Vercel CLI is required (install it, then authenticate with `vercel login`).", file=sys.stderr)
        return 2

    repo = Path(args.api_dir).resolve()
    if not repo.is_dir():
        print(f"ERROR: API project directory does not exist: {repo}", file=sys.stderr)
        return 2

    try:
        if args.provision:
            provision(repo)
        else:
            _ensure_link(repo)
            verify(repo)
    except ProvisioningError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    print(
        "PASS: Vercel Wave 2 external prerequisites are present for preview and production. "
        "Database migrations, GitHub merge, production deployment, and post-deploy verification remain separate operator gates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
