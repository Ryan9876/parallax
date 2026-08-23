from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol

from .common import (
    AcceptedSourceLineage,
    AuthorizedProviderExecutor,
    ProviderActionSuccess,
    ProviderClientError,
    ProviderInvocation,
    ProviderProjectBinding,
    require_app_branch,
    require_https_url,
    require_repository_ref,
    require_source_revision,
    safe_provider_call,
)
from ..registry import ToolCapabilityRegistry


VERCEL_TOOL = "vercel"
ACTION_PREVIEW_CREATE = "preview.create"
ACTION_PREVIEW_READ = "preview.read"

_TARGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_DEPLOYMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class VercelPreviewStatus(str, Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    READY = "READY"
    ERROR = "ERROR"
    CANCELED = "CANCELED"


@dataclass(frozen=True, slots=True)
class VercelPreviewTarget:
    project_ref: str
    repository_ref: str
    vercel_project_ref: str

    def __post_init__(self) -> None:
        binding = ProviderProjectBinding(
            project_ref=self.project_ref,
            repository_ref=self.repository_ref,
        )
        if not isinstance(self.vercel_project_ref, str) or not _TARGET.fullmatch(self.vercel_project_ref):
            raise ValueError("vercel_project_ref must be a bounded registered provider identity")
        object.__setattr__(self, "project_ref", binding.project_ref)


@dataclass(frozen=True, slots=True)
class VercelPreviewResult:
    vercel_project_ref: str
    repository_ref: str
    deployment_id: str
    source_revision: str
    status: VercelPreviewStatus
    url: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.vercel_project_ref, str) or not _TARGET.fullmatch(self.vercel_project_ref):
            raise ValueError("vercel_project_ref must be a bounded provider identity")
        require_repository_ref(self.repository_ref)
        if not isinstance(self.deployment_id, str) or not _DEPLOYMENT.fullmatch(self.deployment_id):
            raise ValueError("deployment_id must be bounded")
        require_source_revision(self.source_revision)
        if not isinstance(self.status, VercelPreviewStatus):
            raise TypeError("status must be VercelPreviewStatus")
        if self.url is not None:
            require_https_url(self.url, field="url", allowed_suffix="vercel.app")
        if self.status is VercelPreviewStatus.READY and self.url is None:
            raise ValueError("ready preview must expose its safe preview URL")


class VercelProviderClient(Protocol):
    def create_preview(
        self,
        vercel_project_ref: str,
        repository_ref: str,
        source_revision: str,
        branch_name: str,
        lineage: AcceptedSourceLineage,
    ) -> VercelPreviewResult: ...

    def read_preview(
        self,
        vercel_project_ref: str,
        deployment_id: str,
    ) -> VercelPreviewResult: ...


class VercelPreviewActions:
    """Preview-only Vercel operations beneath project-scoped authority."""

    def __init__(self, registry: ToolCapabilityRegistry, client: VercelProviderClient) -> None:
        self.executor = AuthorizedProviderExecutor(registry)
        self.client = client

    @staticmethod
    def _binding(target: VercelPreviewTarget) -> ProviderProjectBinding:
        return ProviderProjectBinding(
            project_ref=target.project_ref,
            repository_ref=target.repository_ref,
        )

    @staticmethod
    def _verify_target(target: VercelPreviewTarget, result: VercelPreviewResult) -> None:
        if result.vercel_project_ref != target.vercel_project_ref:
            raise ProviderClientError("TARGET_MISMATCH", result_identity=result.deployment_id)
        if result.repository_ref != target.repository_ref:
            raise ProviderClientError("REPOSITORY_MISMATCH", result_identity=result.deployment_id)

    @staticmethod
    def _verify_lineage(binding: ProviderProjectBinding, lineage: AcceptedSourceLineage) -> None:
        if not isinstance(lineage, AcceptedSourceLineage):
            raise TypeError("lineage must be AcceptedSourceLineage")
        if lineage.project_id != binding.project_ref:
            raise ValueError("accepted source lineage belongs to a different Project")

    def create_preview(
        self,
        target: VercelPreviewTarget,
        invocation: ProviderInvocation,
        *,
        source_revision: str,
        branch_name: str,
        lineage: AcceptedSourceLineage,
    ) -> ProviderActionSuccess[VercelPreviewResult]:
        binding = self._binding(target)
        require_source_revision(source_revision)
        require_app_branch(branch_name)
        self._verify_lineage(binding, lineage)

        request, decision = self.executor.authorize(
            binding=binding,
            invocation=invocation,
            tool=VERCEL_TOOL,
            action=ACTION_PREVIEW_CREATE,
        )
        try:
            value = safe_provider_call(
                lambda: self.client.create_preview(
                    target.vercel_project_ref,
                    target.repository_ref,
                    source_revision,
                    branch_name,
                    lineage,
                )
            )
            self._verify_target(target, value)
            if value.source_revision != source_revision:
                raise ProviderClientError("SOURCE_MISMATCH", result_identity=value.deployment_id)
            if value.status in {VercelPreviewStatus.ERROR, VercelPreviewStatus.CANCELED}:
                raise ProviderClientError(
                    f"PREVIEW_{value.status.value}",
                    result_identity=value.deployment_id,
                )
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_PREVIEW_CREATE,
                error=exc,
                source_revision=source_revision,
                lineage=lineage,
            ) from exc

        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_PREVIEW_CREATE,
            value=value,
            result_code=f"PREVIEW_{value.status.value}",
            result_identity=value.deployment_id,
            source_revision=source_revision,
            lineage=lineage,
            safe_url=value.url,
        )

    def read_preview(
        self,
        target: VercelPreviewTarget,
        invocation: ProviderInvocation,
        *,
        deployment_id: str,
        expected_source_revision: str,
    ) -> ProviderActionSuccess[VercelPreviewResult]:
        binding = self._binding(target)
        if not isinstance(deployment_id, str) or not _DEPLOYMENT.fullmatch(deployment_id):
            raise ValueError("deployment_id must be bounded")
        require_source_revision(expected_source_revision, field="expected_source_revision")

        request, decision = self.executor.authorize(
            binding=binding,
            invocation=invocation,
            tool=VERCEL_TOOL,
            action=ACTION_PREVIEW_READ,
        )
        try:
            value = safe_provider_call(
                lambda: self.client.read_preview(target.vercel_project_ref, deployment_id)
            )
            self._verify_target(target, value)
            if value.deployment_id != deployment_id:
                raise ProviderClientError("DEPLOYMENT_MISMATCH", result_identity=value.deployment_id)
            if value.source_revision != expected_source_revision:
                raise ProviderClientError("SOURCE_MISMATCH", result_identity=value.deployment_id)
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_PREVIEW_READ,
                error=exc,
                source_revision=expected_source_revision,
            ) from exc

        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_PREVIEW_READ,
            value=value,
            result_code=f"PREVIEW_STATUS_{value.status.value}",
            result_identity=value.deployment_id,
            source_revision=value.source_revision,
            safe_url=value.url,
        )
