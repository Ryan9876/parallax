from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from .common import (
    AcceptedSourceLineage,
    ProviderClientError,
    require_app_branch,
    require_repository_ref,
    require_source_revision,
)
from .credentials import VercelCredentialProvider, require_scoped_credential
from .vercel import VercelPreviewResult, VercelPreviewStatus, VercelProviderClient


_VERCEL_API = "https://api.vercel.com"
_BOUNDED_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


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


@dataclass(frozen=True, slots=True)
class VercelApiTarget:
    """Server-owned immutable mapping from #62 target identity to one Vercel project."""

    vercel_project_ref: str
    project_id: str
    project_name: str
    team_id: str | None
    repository_ref: str
    github_repo_id: int
    production_branch: str

    def __post_init__(self) -> None:
        if not isinstance(self.vercel_project_ref, str) or not _BOUNDED_ID.fullmatch(self.vercel_project_ref):
            raise ValueError("Vercel target reference must be bounded")
        if not isinstance(self.project_id, str) or not _BOUNDED_ID.fullmatch(self.project_id):
            raise ValueError("Vercel project ID must be bounded")
        if not isinstance(self.project_name, str) or not _BOUNDED_ID.fullmatch(self.project_name):
            raise ValueError("Vercel project name must be bounded")
        if self.team_id is not None and (
            not isinstance(self.team_id, str) or not _BOUNDED_ID.fullmatch(self.team_id)
        ):
            raise ValueError("Vercel team ID must be bounded")
        require_repository_ref(self.repository_ref)
        if not isinstance(self.github_repo_id, int) or isinstance(self.github_repo_id, bool) or self.github_repo_id < 1:
            raise ValueError("GitHub repository ID must be a positive integer")
        if (
            not isinstance(self.production_branch, str)
            or not _BRANCH.fullmatch(self.production_branch)
            or self.production_branch.startswith("/")
            or "//" in self.production_branch
            or ".." in self.production_branch.split("/")
        ):
            raise ValueError("production branch must be a bounded branch identity")


class VercelPreviewRestClient(VercelProviderClient):
    """Concrete Vercel REST client whose only deployment capability is Preview."""

    def __init__(
        self,
        credential_provider: VercelCredentialProvider,
        targets: Mapping[str, VercelApiTarget],
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 60:
            raise ValueError("Vercel timeout must be between 0 and 60 seconds")
        normalized: dict[str, VercelApiTarget] = {}
        for key, value in dict(targets).items():
            if not isinstance(value, VercelApiTarget) or key != value.vercel_project_ref:
                raise ValueError("Vercel target mapping must use exact target references")
            normalized[key] = value
        self._targets = MappingProxyType(normalized)
        self._credential_provider = credential_provider
        self._http = httpx.Client(
            base_url=_VERCEL_API,
            transport=transport,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )

    def _target(self, vercel_project_ref: str) -> VercelApiTarget:
        target = self._targets.get(vercel_project_ref)
        if target is None:
            raise ProviderClientError("TARGET_NOT_FOUND")
        return target

    def _headers(self, target: VercelApiTarget) -> dict[str, str]:
        try:
            credential = self._credential_provider.credential_for_project(target.vercel_project_ref)
        except ProviderClientError:
            raise
        except Exception:
            raise ProviderClientError("CREDENTIAL_UNAVAILABLE") from None
        credential = require_scoped_credential(
            credential,
            provider="vercel",
            resource_ref=target.vercel_project_ref,
        )
        return {
            "Authorization": credential.authorization_value(),
            "Content-Type": "application/json",
            "User-Agent": "Parallax-App-Builder",
        }

    @staticmethod
    def _params(api_target: VercelApiTarget, **extra: object) -> dict[str, object]:
        params: dict[str, object] = dict(extra)
        if api_target.team_id is not None:
            params["teamId"] = api_target.team_id
        return params

    def _send(
        self,
        method: str,
        target: VercelApiTarget,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        try:
            return self._http.request(
                method,
                path,
                headers=self._headers(target),
                params=params,
                json=json,
            )
        except ProviderClientError:
            raise
        except httpx.TimeoutException:
            raise ProviderClientError("PROVIDER_TIMEOUT") from None
        except httpx.RequestError:
            raise ProviderClientError("PROVIDER_UNAVAILABLE") from None
        except Exception:
            raise ProviderClientError("PROVIDER_ERROR") from None

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
            if response.headers.get("retry-after"):
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
        except Exception:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from None

    def _verify_project(self, target: VercelApiTarget) -> None:
        response = self._send(
            "GET",
            target,
            f"/v9/projects/{quote(target.project_id, safe='')}",
            params=self._params(target),
        )
        self._raise_status(response, not_found="TARGET_NOT_FOUND")
        payload = _dict(self._json(response))
        if payload.get("id") != target.project_id or payload.get("name") != target.project_name:
            raise ProviderClientError("TARGET_MISMATCH")
        link_payload = _dict(payload.get("link"))
        if link_payload.get("type") != "github":
            raise ProviderClientError("REPOSITORY_MISMATCH")
        repo_id = link_payload.get("repoId")
        if repo_id is None or str(repo_id) != str(target.github_repo_id):
            raise ProviderClientError("REPOSITORY_MISMATCH")

    @staticmethod
    def _status(value: object) -> VercelPreviewStatus:
        if not isinstance(value, str):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        normalized = value.upper()
        if normalized == "INITIALIZING":
            return VercelPreviewStatus.QUEUED
        if normalized == "BLOCKED":
            return VercelPreviewStatus.ERROR
        try:
            return VercelPreviewStatus(normalized)
        except ValueError:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from None

    def _parse_preview(
        self,
        target: VercelApiTarget,
        payload: dict[str, Any],
        *,
        expected_source_revision: str | None = None,
        expected_branch: str | None = None,
    ) -> VercelPreviewResult:
        deployment_target = payload.get("target")
        if not isinstance(deployment_target, str) or deployment_target.casefold() != "preview":
            raise ProviderClientError("PRODUCTION_SCOPE_FORBIDDEN")

        project = payload.get("project")
        if isinstance(project, dict):
            if project.get("id") != target.project_id or project.get("name") != target.project_name:
                raise ProviderClientError("TARGET_MISMATCH")
        elif payload.get("projectId") == target.project_id:
            pass
        else:
            raise ProviderClientError("TARGET_MISMATCH")

        git_source = _dict(payload.get("gitSource"))
        source_type = git_source.get("type")
        if not isinstance(source_type, str) or not source_type.casefold().startswith("github"):
            raise ProviderClientError("REPOSITORY_MISMATCH")
        repo_id = git_source.get("repoId")
        if repo_id is None or str(repo_id) != str(target.github_repo_id):
            raise ProviderClientError("REPOSITORY_MISMATCH")
        source_revision = _string(git_source.get("sha"))
        if expected_source_revision is not None and source_revision != expected_source_revision:
            raise ProviderClientError("SOURCE_MISMATCH")
        if expected_branch is not None and git_source.get("ref") != expected_branch:
            raise ProviderClientError("SOURCE_MISMATCH")

        deployment_id = payload.get("id", payload.get("uid"))
        deployment_id = _string(deployment_id)
        state = payload.get("readyState", payload.get("state", payload.get("status")))
        status = self._status(state)
        raw_url = payload.get("url")
        url: str | None = None
        if raw_url is not None:
            raw_url = _string(raw_url)
            url = raw_url if raw_url.startswith("https://") else f"https://{raw_url}"

        return VercelPreviewResult(
            target.vercel_project_ref,
            target.repository_ref,
            deployment_id,
            source_revision,
            status,
            url,
        )

    def _read_preview(
        self,
        target: VercelApiTarget,
        deployment_id: str,
        *,
        expected_source_revision: str | None = None,
        expected_branch: str | None = None,
    ) -> VercelPreviewResult:
        response = self._send(
            "GET",
            target,
            f"/v13/deployments/{quote(deployment_id, safe='')}",
            params=self._params(target, withGitRepoInfo="true"),
        )
        self._raise_status(response, not_found="DEPLOYMENT_NOT_FOUND")
        return self._parse_preview(
            target,
            _dict(self._json(response)),
            expected_source_revision=expected_source_revision,
            expected_branch=expected_branch,
        )

    def _find_existing_preview(
        self,
        target: VercelApiTarget,
        *,
        source_revision: str,
        branch_name: str,
    ) -> VercelPreviewResult | None:
        response = self._send(
            "GET",
            target,
            "/v6/deployments",
            params=self._params(
                target,
                projectId=target.project_id,
                target="preview",
                branch=branch_name,
                sha=source_revision,
                limit=10,
            ),
        )
        self._raise_status(response)
        payload = _dict(self._json(response))
        deployments = _list(payload.get("deployments"))
        for raw in deployments:
            item = _dict(raw)
            deployment_id = item.get("id", item.get("uid"))
            if not isinstance(deployment_id, str) or not deployment_id:
                raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
            return self._read_preview(
                target,
                deployment_id,
                expected_source_revision=source_revision,
                expected_branch=branch_name,
            )
        return None

    def create_preview(
        self,
        vercel_project_ref: str,
        repository_ref: str,
        source_revision: str,
        branch_name: str,
        lineage: AcceptedSourceLineage,
    ) -> VercelPreviewResult:
        target = self._target(vercel_project_ref)
        require_repository_ref(repository_ref)
        require_source_revision(source_revision)
        require_app_branch(branch_name)
        if repository_ref != target.repository_ref:
            raise ProviderClientError("REPOSITORY_MISMATCH")
        if not isinstance(lineage, AcceptedSourceLineage):
            raise TypeError("lineage must be AcceptedSourceLineage")
        if branch_name == target.production_branch:
            raise ProviderClientError("PRODUCTION_BRANCH_FORBIDDEN")

        self._verify_project(target)
        existing = self._find_existing_preview(
            target,
            source_revision=source_revision,
            branch_name=branch_name,
        )
        if existing is not None:
            return existing

        response = self._send(
            "POST",
            target,
            "/v13/deployments",
            params=self._params(target),
            json={
                "name": target.project_name,
                "project": target.project_id,
                "target": "preview",
                "gitSource": {
                    "type": "github",
                    "repoId": target.github_repo_id,
                    "ref": branch_name,
                    "sha": source_revision,
                },
            },
        )
        if response.status_code in {409, 422, 429}:
            replay = self._find_existing_preview(
                target,
                source_revision=source_revision,
                branch_name=branch_name,
            )
            if replay is not None:
                return replay
            self._raise_status(response, conflict="PREVIEW_CONFLICT")
        self._raise_status(response, conflict="PREVIEW_CONFLICT")
        return self._parse_preview(
            target,
            _dict(self._json(response)),
            expected_source_revision=source_revision,
            expected_branch=branch_name,
        )

    def read_preview(
        self,
        vercel_project_ref: str,
        deployment_id: str,
    ) -> VercelPreviewResult:
        target = self._target(vercel_project_ref)
        return self._read_preview(target, deployment_id)
