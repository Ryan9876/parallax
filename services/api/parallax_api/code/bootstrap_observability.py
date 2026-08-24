from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from ..tools.providers import (
    ACTION_REPOSITORY_RESOLVE,
    ACTION_SOURCE_FILE_READ,
    ACTION_SOURCE_TREE_READ,
    ProviderActionDenied,
    ProviderActionFailed,
    ProviderClientError,
)
from .lineage_persistence import MetadataStoreError, ObjectStoreError
from .workspace_lineage import LineageIntegrityError, SourcePolicyError, SourceProviderError


logger = logging.getLogger("parallax.bootstrap")

_SAFE_DIAGNOSTIC = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
_PROVIDER_STAGE = {
    ACTION_REPOSITORY_RESOLVE: "provider-repository",
    ACTION_SOURCE_TREE_READ: "provider-tree",
    ACTION_SOURCE_FILE_READ: "provider-file",
}
_ALLOWED_STAGES = frozenset(
    {
        "lineage-head",
        "project-binding",
        "provider-repository",
        "provider-tree",
        "provider-file",
        "provider-client",
        "provider-authority",
        "source-provider",
        "source-policy",
        "object-store",
        "metadata-store",
        "lineage-integrity",
        "lineage-initialize",
        "materialization-cleanup",
        "bootstrap-contract",
    }
)


@dataclass(frozen=True, slots=True)
class BootstrapFailureEvidence:
    stage: str
    error_class: str
    result_code: str | None = None

    def __post_init__(self) -> None:
        if self.stage not in _ALLOWED_STAGES:
            raise ValueError("bootstrap diagnostic stage is not registered")
        if _SAFE_DIAGNOSTIC.fullmatch(self.error_class) is None:
            raise ValueError("bootstrap diagnostic error class is not bounded")
        if self.result_code is not None and _SAFE_DIAGNOSTIC.fullmatch(self.result_code) is None:
            raise ValueError("bootstrap diagnostic result code is not bounded")


def _exception_chain(exc: BaseException) -> tuple[BaseException, ...]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(chain) < 16:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__
    return tuple(chain)


def _safe_value(value: object) -> str | None:
    if not isinstance(value, str) or _SAFE_DIAGNOSTIC.fullmatch(value) is None:
        return None
    return value


def classify_bootstrap_failure(
    exc: BaseException,
    *,
    default_stage: str,
) -> BootstrapFailureEvidence:
    if default_stage not in _ALLOWED_STAGES:
        raise ValueError("default bootstrap diagnostic stage is not registered")

    chain = _exception_chain(exc)

    for item in chain:
        if isinstance(item, (ProviderActionFailed, ProviderActionDenied)):
            action = getattr(getattr(item, "evidence", None), "action", None)
            result_code = getattr(getattr(item, "evidence", None), "result_status", None)
            stage = _PROVIDER_STAGE.get(action, "provider-authority" if isinstance(item, ProviderActionDenied) else "provider-client")
            return BootstrapFailureEvidence(
                stage=stage,
                error_class=type(item).__name__,
                result_code=_safe_value(result_code),
            )

    for item in chain:
        if isinstance(item, ProviderClientError):
            return BootstrapFailureEvidence(
                stage="provider-client",
                error_class=type(item).__name__,
                result_code=_safe_value(item.result.result_code),
            )

    for item in chain:
        if isinstance(item, ObjectStoreError):
            return BootstrapFailureEvidence(stage="object-store", error_class=type(item).__name__)
        if isinstance(item, MetadataStoreError):
            return BootstrapFailureEvidence(stage="metadata-store", error_class=type(item).__name__)
        if isinstance(item, SourcePolicyError):
            return BootstrapFailureEvidence(stage="source-policy", error_class=type(item).__name__)
        if isinstance(item, SourceProviderError):
            return BootstrapFailureEvidence(stage="source-provider", error_class=type(item).__name__)
        if isinstance(item, LineageIntegrityError):
            return BootstrapFailureEvidence(stage="lineage-integrity", error_class=type(item).__name__)

    return BootstrapFailureEvidence(
        stage=default_stage,
        error_class=type(exc).__name__ if _SAFE_DIAGNOSTIC.fullmatch(type(exc).__name__) else "Exception",
    )


def record_bootstrap_failure(
    exc: BaseException,
    *,
    default_stage: str,
) -> BootstrapFailureEvidence:
    evidence = classify_bootstrap_failure(exc, default_stage=default_stage)
    logger.error(
        "source_bootstrap_failed stage=%s error_class=%s result_code=%s",
        evidence.stage,
        evidence.error_class,
        evidence.result_code or "none",
    )
    return evidence


__all__ = [
    "BootstrapFailureEvidence",
    "classify_bootstrap_failure",
    "record_bootstrap_failure",
]
