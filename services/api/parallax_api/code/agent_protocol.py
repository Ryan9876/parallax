from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import math
from pathlib import PurePosixPath
import re
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


AGENT_PROTOCOL_VERSION = 1
_MAX_ACCEPTANCE_IDS = 128
_MAX_CONTEXT_REFS = 64
_MAX_CAPABILITY_TOKENS = 64
_MAX_CHANGED_PATHS = 128
_MAX_METRICS = 16
_MAX_SUMMARY_BYTES = 512
_MAX_REFERENCE_BYTES = 192

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTANCE_ID_RE = re.compile(r"^AC-[0-9]{2,3}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SAFE_UNIT_RE = re.compile(r"^[a-z][a-z0-9._/-]{0,31}$")
_SAFE_PATH_PART_RE = re.compile(r"^[A-Za-z0-9._@+ -]{1,96}$")
_SENSITIVE_SUMMARY_RE = re.compile(
    r"(?:authorization\s*:|bearer\s+[A-Za-z0-9._-]+|api[_ -]?key|password\s*=|token\s*=|"
    r"-----BEGIN [A-Z ]+PRIVATE KEY-----|https?://)",
    re.IGNORECASE,
)
_SENSITIVE_REFERENCE_RE = re.compile(
    r"(?:authorization|bearer|api[_-]?key|access[_-]?token|credential|cookie|secret|password|"
    r"connection[_-]?string)",
    re.IGNORECASE,
)
_SENSITIVE_PATH_PARTS = frozenset({".npmrc", ".pypirc", "credentials", "secrets"})


class AgentProtocolError(ValueError):
    pass


class AgentLifecycleStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    COMPLETED = "COMPLETED"
    RECOVERABLE_FAILURE = "RECOVERABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


_TERMINAL_STATUSES = frozenset(
    {
        AgentLifecycleStatus.COMPLETED,
        AgentLifecycleStatus.TERMINAL_FAILURE,
        AgentLifecycleStatus.TIMEOUT,
        AgentLifecycleStatus.CANCELLED,
        AgentLifecycleStatus.REJECTED,
    }
)


class EvidenceKind(StrEnum):
    SOURCE = "SOURCE"
    ARTIFACT = "ARTIFACT"
    TEST = "TEST"
    DIAGNOSTIC = "DIAGNOSTIC"
    CHECKPOINT = "CHECKPOINT"
    OBSERVATION = "OBSERVATION"


class MetricName(StrEnum):
    DURATION = "duration"
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    REQUESTS = "requests"
    COST = "cost"


class MetricAvailability(StrEnum):
    OBSERVED = "OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class MetricProvenanceKind(StrEnum):
    PROVIDER = "PROVIDER"
    PARALLAX = "PARALLAX"
    ESTIMATE = "ESTIMATE"


class AdmissionReason(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    RUN_MISMATCH = "RUN_MISMATCH"
    WORK_SPECIFICATION_MISMATCH = "WORK_SPECIFICATION_MISMATCH"
    ACCEPTANCE_CONTRACT_MISMATCH = "ACCEPTANCE_CONTRACT_MISMATCH"
    OPERATION_MISMATCH = "OPERATION_MISMATCH"
    REQUEST_MISMATCH = "REQUEST_MISMATCH"
    ATTEMPT_MISMATCH = "ATTEMPT_MISMATCH"
    AGENT_IDENTITY_MISMATCH = "AGENT_IDENTITY_MISMATCH"
    SOURCE_CONTEXT_MISMATCH = "SOURCE_CONTEXT_MISMATCH"
    STALE_ATTEMPT = "STALE_ATTEMPT"
    REVOKED = "REVOKED"
    COMPETING_TERMINAL_RESULT = "COMPETING_TERMINAL_RESULT"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    agent_id: str
    agent_version: str
    adapter_id: str
    adapter_version: str
    provider_kind: str
    declared_work_kinds: tuple[str, ...]
    declared_capabilities: tuple[str, ...] = ()
    model_runtime_label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "agent_id", _token(self.agent_id, field="agent_id"))
        object.__setattr__(self, "agent_version", _version(self.agent_version, field="agent_version"))
        object.__setattr__(self, "adapter_id", _token(self.adapter_id, field="adapter_id"))
        object.__setattr__(self, "adapter_version", _version(self.adapter_version, field="adapter_version"))
        object.__setattr__(self, "provider_kind", _token(self.provider_kind, field="provider_kind"))
        object.__setattr__(
            self,
            "declared_work_kinds",
            _token_set(self.declared_work_kinds, field="declared_work_kinds", required=True),
        )
        object.__setattr__(
            self,
            "declared_capabilities",
            _token_set(self.declared_capabilities, field="declared_capabilities"),
        )
        if self.model_runtime_label is not None:
            object.__setattr__(
                self,
                "model_runtime_label",
                _reference(self.model_runtime_label, field="model_runtime_label"),
            )

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "provider_kind": self.provider_kind,
            "declared_work_kinds": list(self.declared_work_kinds),
            "declared_capabilities": list(self.declared_capabilities),
            "model_runtime_label": self.model_runtime_label,
            "grants_authority": False,
            "contains_credentials": False,
        }


@dataclass(frozen=True, slots=True)
class AgentSourceContext:
    lineage_id: str
    revision_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "lineage_id", _sha256(self.lineage_id, field="lineage_id"))
        object.__setattr__(self, "revision_id", _reference(self.revision_id, field="revision_id"))

    def as_dict(self) -> dict[str, str]:
        return {"lineage_id": self.lineage_id, "revision_id": self.revision_id}


@dataclass(frozen=True, slots=True)
class AgentEvidenceReference:
    kind: EvidenceKind
    reference_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        try:
            kind = self.kind if isinstance(self.kind, EvidenceKind) else EvidenceKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise AgentProtocolError("invalid evidence kind") from exc
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "reference_id", _reference(self.reference_id, field="reference_id"))
        if self.digest is not None:
            object.__setattr__(self, "digest", _sha256(self.digest, field="digest"))

    def as_dict(self) -> dict[str, str | None]:
        return {"kind": self.kind.value, "reference_id": self.reference_id, "digest": self.digest}


@dataclass(frozen=True, slots=True)
class AgentTaskBinding:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    operation_id: str
    request_id: str
    attempt_number: int
    attempt_id: str
    agent_identity_digest: str
    source_context: AgentSourceContext | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, field="project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, field="run_id"))
        object.__setattr__(
            self,
            "work_specification_id",
            _uuid(self.work_specification_id, field="work_specification_id"),
        )
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise AgentProtocolError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha256(self.work_specification_digest, field="work_specification_digest"),
        )
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        object.__setattr__(self, "operation_id", _reference(self.operation_id, field="operation_id"))
        object.__setattr__(self, "request_id", _reference(self.request_id, field="request_id"))
        if (
            not isinstance(self.attempt_number, int)
            or isinstance(self.attempt_number, bool)
            or self.attempt_number < 1
        ):
            raise AgentProtocolError("attempt_number must be >= 1")
        object.__setattr__(self, "attempt_id", _reference(self.attempt_id, field="attempt_id"))
        object.__setattr__(
            self,
            "agent_identity_digest",
            _sha256(self.agent_identity_digest, field="agent_identity_digest"),
        )
        if self.source_context is not None and not isinstance(self.source_context, AgentSourceContext):
            raise AgentProtocolError("source_context must be AgentSourceContext")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "operation_id": self.operation_id,
            "request_id": self.request_id,
            "attempt_number": self.attempt_number,
            "attempt_id": self.attempt_id,
            "agent_identity_digest": self.agent_identity_digest,
            "source_context": self.source_context.as_dict() if self.source_context is not None else None,
        }


@dataclass(frozen=True, slots=True)
class AgentTaskRequest:
    binding: AgentTaskBinding
    agent: AgentIdentity
    work_kind: str
    requested_capabilities: tuple[str, ...] = ()
    context_refs: tuple[AgentEvidenceReference, ...] = ()
    created_at: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    deadline_at: datetime | None = None
    cancel_requested_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.binding, AgentTaskBinding) or not isinstance(self.agent, AgentIdentity):
            raise AgentProtocolError("binding and agent are required canonical values")
        if self.binding.agent_identity_digest != self.agent.digest:
            raise AgentProtocolError("task binding does not match agent identity")
        object.__setattr__(self, "work_kind", _token(self.work_kind, field="work_kind"))
        if self.work_kind not in self.agent.declared_work_kinds:
            raise AgentProtocolError("work_kind is not declared by the bound agent")
        object.__setattr__(
            self,
            "requested_capabilities",
            _token_set(self.requested_capabilities, field="requested_capabilities"),
        )
        if any(capability not in self.agent.declared_capabilities for capability in self.requested_capabilities):
            raise AgentProtocolError("requested capability is not declared by the bound agent")
        refs = tuple(self.context_refs)
        if len(refs) > _MAX_CONTEXT_REFS or any(
            not isinstance(item, AgentEvidenceReference) for item in refs
        ):
            raise AgentProtocolError("context_refs must contain bounded evidence references")
        if len({(item.kind, item.reference_id, item.digest) for item in refs}) != len(refs):
            raise AgentProtocolError("context_refs must be unique")
        object.__setattr__(self, "context_refs", refs)

        created = _aware_utc(self.created_at, field="created_at")
        object.__setattr__(self, "created_at", created)
        if self.deadline_at is not None:
            deadline = _aware_utc(self.deadline_at, field="deadline_at")
            if deadline <= created:
                raise AgentProtocolError("deadline_at must be after created_at")
            object.__setattr__(self, "deadline_at", deadline)
        if self.cancel_requested_at is not None:
            cancelled = _aware_utc(self.cancel_requested_at, field="cancel_requested_at")
            if cancelled < created:
                raise AgentProtocolError("cancel_requested_at cannot precede created_at")
            object.__setattr__(self, "cancel_requested_at", cancelled)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        run_id: str,
        work_specification_id: str,
        work_specification_revision: int,
        work_specification_digest: str,
        acceptance_ids: tuple[str, ...],
        operation_id: str,
        request_id: str,
        attempt_number: int,
        attempt_id: str,
        agent: AgentIdentity,
        work_kind: str,
        source_context: AgentSourceContext | None = None,
        requested_capabilities: tuple[str, ...] = (),
        context_refs: tuple[AgentEvidenceReference, ...] = (),
        created_at: datetime | None = None,
        deadline_at: datetime | None = None,
        cancel_requested_at: datetime | None = None,
    ) -> AgentTaskRequest:
        if not isinstance(agent, AgentIdentity):
            raise AgentProtocolError("agent must be AgentIdentity")
        binding = AgentTaskBinding(
            project_id=project_id,
            run_id=run_id,
            work_specification_id=work_specification_id,
            work_specification_revision=work_specification_revision,
            work_specification_digest=work_specification_digest,
            acceptance_ids=acceptance_ids,
            operation_id=operation_id,
            request_id=request_id,
            attempt_number=attempt_number,
            attempt_id=attempt_id,
            agent_identity_digest=agent.digest,
            source_context=source_context,
        )
        return cls(
            binding=binding,
            agent=agent,
            work_kind=work_kind,
            requested_capabilities=requested_capabilities,
            context_refs=context_refs,
            created_at=created_at or datetime.now(timezone.utc),
            deadline_at=deadline_at,
            cancel_requested_at=cancel_requested_at,
        )

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol_version": AGENT_PROTOCOL_VERSION,
            "binding": self.binding.as_dict(),
            "agent": self.agent.as_dict(),
            "work_kind": self.work_kind,
            "requested_capabilities": list(self.requested_capabilities),
            "context_refs": [item.as_dict() for item in self.context_refs],
            "created_at": _iso(self.created_at),
            "deadline_at": _iso(self.deadline_at),
            "cancel_requested_at": _iso(self.cancel_requested_at),
            "capabilities_are_authority": False,
            "contains_raw_provider_payload": False,
            "contains_hidden_reasoning": False,
            "contains_credentials": False,
        }


@dataclass(frozen=True, slots=True)
class MetricObservation:
    metric: MetricName
    availability: MetricAvailability
    source: str
    value: float | int | None = None
    unit: str | None = None
    currency: str | None = None
    provenance_kind: MetricProvenanceKind | None = None
    provenance_ref: str | None = None

    def __post_init__(self) -> None:
        try:
            metric = self.metric if isinstance(self.metric, MetricName) else MetricName(self.metric)
            availability = (
                self.availability
                if isinstance(self.availability, MetricAvailability)
                else MetricAvailability(self.availability)
            )
        except (TypeError, ValueError) as exc:
            raise AgentProtocolError("invalid metric observation enum") from exc
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "source", _token(self.source, field="source"))

        if availability is MetricAvailability.OBSERVED:
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise AgentProtocolError("observed metric requires numeric value")
            if not math.isfinite(float(self.value)) or float(self.value) < 0:
                raise AgentProtocolError("observed metric value must be finite and non-negative")
            if not isinstance(self.unit, str) or not _SAFE_UNIT_RE.fullmatch(self.unit):
                raise AgentProtocolError("observed metric requires bounded unit")
            if self.provenance_kind is None:
                raise AgentProtocolError("observed metric requires provenance_kind")
            try:
                provenance_kind = (
                    self.provenance_kind
                    if isinstance(self.provenance_kind, MetricProvenanceKind)
                    else MetricProvenanceKind(self.provenance_kind)
                )
            except (TypeError, ValueError) as exc:
                raise AgentProtocolError("invalid metric provenance") from exc
            object.__setattr__(self, "provenance_kind", provenance_kind)
            if self.provenance_ref is None:
                raise AgentProtocolError("observed metric requires provenance_ref")
            object.__setattr__(
                self,
                "provenance_ref",
                _reference(self.provenance_ref, field="provenance_ref"),
            )
            if metric is MetricName.COST:
                if not isinstance(self.currency, str) or not _CURRENCY_RE.fullmatch(self.currency):
                    raise AgentProtocolError("observed cost requires ISO-style currency")
            elif self.currency is not None:
                raise AgentProtocolError("currency is only valid for cost")
        else:
            if any(
                item is not None
                for item in (
                    self.value,
                    self.unit,
                    self.currency,
                    self.provenance_kind,
                    self.provenance_ref,
                )
            ):
                raise AgentProtocolError("unavailable/unknown metrics cannot fabricate observed fields")

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "availability": self.availability.value,
            "source": self.source,
            "value": self.value,
            "unit": self.unit,
            "currency": self.currency,
            "provenance_kind": self.provenance_kind.value if self.provenance_kind else None,
            "provenance_ref": self.provenance_ref,
        }


@dataclass(frozen=True, slots=True)
class AgentCheckpoint:
    binding: AgentTaskBinding
    agent: AgentIdentity
    checkpoint_id: str
    summary: str
    evidence_refs: tuple[AgentEvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        _verify_bound_agent(self.binding, self.agent)
        object.__setattr__(self, "checkpoint_id", _reference(self.checkpoint_id, field="checkpoint_id"))
        object.__setattr__(self, "summary", _safe_summary(self.summary))
        object.__setattr__(self, "evidence_refs", _evidence_refs(self.evidence_refs))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol_version": AGENT_PROTOCOL_VERSION,
            "binding": self.binding.as_dict(),
            "agent": self.agent.as_dict(),
            "checkpoint_id": self.checkpoint_id,
            "summary": self.summary,
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
            "grants_worker_authority": False,
            "contains_provider_payload": False,
            "contains_credentials": False,
            "contains_hidden_reasoning": False,
        }


@dataclass(frozen=True, slots=True)
class AgentResult:
    binding: AgentTaskBinding
    agent: AgentIdentity
    status: AgentLifecycleStatus
    reason_code: str | None
    summary: str
    claimed_acceptance_ids: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    evidence_refs: tuple[AgentEvidenceReference, ...] = ()
    metrics: tuple[MetricObservation, ...] = ()
    checkpoint: AgentCheckpoint | None = None

    def __post_init__(self) -> None:
        _verify_bound_agent(self.binding, self.agent)
        try:
            status = (
                self.status
                if isinstance(self.status, AgentLifecycleStatus)
                else AgentLifecycleStatus(self.status)
            )
        except (TypeError, ValueError) as exc:
            raise AgentProtocolError("invalid result status") from exc
        if status in {AgentLifecycleStatus.ACCEPTED, AgentLifecycleStatus.STARTED, AgentLifecycleStatus.RUNNING}:
            raise AgentProtocolError("AgentResult requires checkpointed or outcome status")
        object.__setattr__(self, "status", status)
        if self.reason_code is not None:
            if not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(self.reason_code):
                raise AgentProtocolError("reason_code must be a bounded normalized code")
        if status is AgentLifecycleStatus.COMPLETED and self.reason_code is not None:
            raise AgentProtocolError("completed result cannot contain failure reason")
        if status is not AgentLifecycleStatus.COMPLETED and self.reason_code is None:
            raise AgentProtocolError("non-success result requires reason_code")
        object.__setattr__(self, "summary", _safe_summary(self.summary))
        claimed = tuple(self.claimed_acceptance_ids)
        if len(claimed) > _MAX_ACCEPTANCE_IDS:
            raise AgentProtocolError("too many claimed acceptance ids")
        for item in claimed:
            if not isinstance(item, str) or not _ACCEPTANCE_ID_RE.fullmatch(item):
                raise AgentProtocolError("invalid claimed acceptance id")
        if len(set(claimed)) != len(claimed):
            raise AgentProtocolError("claimed acceptance ids must be unique")
        object.__setattr__(self, "claimed_acceptance_ids", claimed)

        paths = tuple(_safe_path(item) for item in self.changed_paths)
        if len(paths) > _MAX_CHANGED_PATHS or len(set(paths)) != len(paths):
            raise AgentProtocolError("changed_paths must be bounded and unique")
        object.__setattr__(self, "changed_paths", paths)
        object.__setattr__(self, "evidence_refs", _evidence_refs(self.evidence_refs))

        metrics = tuple(self.metrics)
        if len(metrics) > _MAX_METRICS or any(not isinstance(item, MetricObservation) for item in metrics):
            raise AgentProtocolError("metrics must contain bounded MetricObservation values")
        if len({item.metric for item in metrics}) != len(metrics):
            raise AgentProtocolError("metric names must be unique")
        object.__setattr__(self, "metrics", metrics)

        if self.checkpoint is not None:
            if not isinstance(self.checkpoint, AgentCheckpoint):
                raise AgentProtocolError("checkpoint must be AgentCheckpoint")
            if self.checkpoint.binding != self.binding or self.checkpoint.agent.digest != self.agent.digest:
                raise AgentProtocolError("checkpoint identity does not match result")
            if status not in {
                AgentLifecycleStatus.CHECKPOINTED,
                AgentLifecycleStatus.RECOVERABLE_FAILURE,
            }:
                raise AgentProtocolError("checkpoint is only valid for checkpoint/recoverable results")
        if status is AgentLifecycleStatus.RECOVERABLE_FAILURE and self.checkpoint is None:
            raise AgentProtocolError("recoverable failure requires checkpoint evidence")

    @property
    def terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol_version": AGENT_PROTOCOL_VERSION,
            "binding": self.binding.as_dict(),
            "agent": self.agent.as_dict(),
            "status": self.status.value,
            "reason_code": self.reason_code,
            "summary": self.summary,
            "claimed_acceptance_ids": list(self.claimed_acceptance_ids),
            "changed_paths": list(self.changed_paths),
            "evidence_refs": [item.as_dict() for item in self.evidence_refs],
            "metrics": [item.as_dict() for item in self.metrics],
            "checkpoint": self.checkpoint.as_dict() if self.checkpoint is not None else None,
            "claimed_acceptance_is_authoritative": False,
            "accepts_source_lineage": False,
            "performs_validation": False,
            "transitions_engineering_run": False,
            "grants_authority": False,
            "contains_provider_payload": False,
            "contains_credentials": False,
            "contains_hidden_reasoning": False,
        }


@dataclass(frozen=True, slots=True)
class AgentLifecycleEvidence:
    binding: AgentTaskBinding
    agent: AgentIdentity
    status: AgentLifecycleStatus
    reason_code: str | None = None
    summary: str = "lifecycle update"

    def __post_init__(self) -> None:
        _verify_bound_agent(self.binding, self.agent)
        try:
            status = (
                self.status
                if isinstance(self.status, AgentLifecycleStatus)
                else AgentLifecycleStatus(self.status)
            )
        except (TypeError, ValueError) as exc:
            raise AgentProtocolError("invalid lifecycle status") from exc
        object.__setattr__(self, "status", status)
        if self.reason_code is not None and (
            not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(self.reason_code)
        ):
            raise AgentProtocolError("reason_code must be a bounded normalized code")
        if status is AgentLifecycleStatus.COMPLETED and self.reason_code is not None:
            raise AgentProtocolError("completed lifecycle evidence cannot contain failure reason")
        if status in {
            AgentLifecycleStatus.RECOVERABLE_FAILURE,
            AgentLifecycleStatus.TERMINAL_FAILURE,
            AgentLifecycleStatus.TIMEOUT,
            AgentLifecycleStatus.CANCELLED,
            AgentLifecycleStatus.REJECTED,
        } and self.reason_code is None:
            raise AgentProtocolError("failure lifecycle evidence requires reason_code")
        object.__setattr__(self, "summary", _safe_summary(self.summary))

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol_version": AGENT_PROTOCOL_VERSION,
            "binding": self.binding.as_dict(),
            "agent": self.agent.as_dict(),
            "status": self.status.value,
            "reason_code": self.reason_code,
            "summary": self.summary,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    admitted: bool
    reason: AdmissionReason
    evidence_digest: str
    duplicate: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.admitted, bool) or not isinstance(self.duplicate, bool):
            raise AgentProtocolError("admission flags must be bool")
        try:
            reason = self.reason if isinstance(self.reason, AdmissionReason) else AdmissionReason(self.reason)
        except (TypeError, ValueError) as exc:
            raise AgentProtocolError("invalid admission reason") from exc
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "evidence_digest", _sha256(self.evidence_digest, field="evidence_digest"))
        if self.duplicate and (self.admitted or reason is not AdmissionReason.DUPLICATE):
            raise AgentProtocolError("duplicate decision cannot admit authority-bearing work")

    def as_dict(self) -> dict[str, object]:
        return {
            "admitted": self.admitted,
            "reason": self.reason.value,
            "evidence_digest": self.evidence_digest,
            "duplicate": self.duplicate,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
        }


def verify_result_admission(
    *,
    expected_task: AgentTaskRequest,
    result: AgentResult,
    current_attempt_number: int | None = None,
    revoked: bool = False,
    accepted_terminal_digest: str | None = None,
) -> AdmissionDecision:
    if not isinstance(expected_task, AgentTaskRequest) or not isinstance(result, AgentResult):
        raise AgentProtocolError("expected_task and result must be canonical protocol values")
    mismatch = _binding_mismatch(expected_task.binding, result.binding)
    if mismatch is not None:
        return _reject(result.digest, mismatch)
    if result.agent.digest != expected_task.agent.digest:
        return _reject(result.digest, AdmissionReason.AGENT_IDENTITY_MISMATCH)
    if current_attempt_number is not None:
        if (
            not isinstance(current_attempt_number, int)
            or isinstance(current_attempt_number, bool)
            or current_attempt_number < 1
        ):
            raise AgentProtocolError("current_attempt_number must be >= 1")
        if result.binding.attempt_number < current_attempt_number:
            return _reject(result.digest, AdmissionReason.STALE_ATTEMPT)
        if result.binding.attempt_number > current_attempt_number:
            return _reject(result.digest, AdmissionReason.ATTEMPT_MISMATCH)
    cancellation_active = revoked or expected_task.cancel_requested_at is not None
    if cancellation_active and result.status is not AgentLifecycleStatus.CANCELLED:
        return _reject(result.digest, AdmissionReason.REVOKED)
    if accepted_terminal_digest is not None:
        accepted = _sha256(accepted_terminal_digest, field="accepted_terminal_digest")
        if not result.terminal:
            return _reject(result.digest, AdmissionReason.COMPETING_TERMINAL_RESULT)
        if accepted == result.digest:
            return AdmissionDecision(
                admitted=False,
                reason=AdmissionReason.DUPLICATE,
                evidence_digest=result.digest,
                duplicate=True,
            )
        return _reject(result.digest, AdmissionReason.COMPETING_TERMINAL_RESULT)
    return AdmissionDecision(
        admitted=True,
        reason=AdmissionReason.ACCEPTED,
        evidence_digest=result.digest,
    )


def verify_checkpoint_admission(
    *,
    expected_task: AgentTaskRequest,
    checkpoint: AgentCheckpoint,
    current_attempt_number: int | None = None,
    revoked: bool = False,
) -> AdmissionDecision:
    if not isinstance(expected_task, AgentTaskRequest) or not isinstance(checkpoint, AgentCheckpoint):
        raise AgentProtocolError("expected_task and checkpoint must be canonical protocol values")
    mismatch = _binding_mismatch(expected_task.binding, checkpoint.binding)
    if mismatch is not None:
        return _reject(checkpoint.digest, mismatch)
    if checkpoint.agent.digest != expected_task.agent.digest:
        return _reject(checkpoint.digest, AdmissionReason.AGENT_IDENTITY_MISMATCH)
    if current_attempt_number is not None:
        if (
            not isinstance(current_attempt_number, int)
            or isinstance(current_attempt_number, bool)
            or current_attempt_number < 1
        ):
            raise AgentProtocolError("current_attempt_number must be >= 1")
        if checkpoint.binding.attempt_number < current_attempt_number:
            return _reject(checkpoint.digest, AdmissionReason.STALE_ATTEMPT)
        if checkpoint.binding.attempt_number > current_attempt_number:
            return _reject(checkpoint.digest, AdmissionReason.ATTEMPT_MISMATCH)
    if revoked or expected_task.cancel_requested_at is not None:
        return _reject(checkpoint.digest, AdmissionReason.REVOKED)
    return AdmissionDecision(
        admitted=True,
        reason=AdmissionReason.ACCEPTED,
        evidence_digest=checkpoint.digest,
    )


@runtime_checkable
class AgentAdapter(Protocol):
    def describe(self) -> AgentIdentity: ...

    async def invoke(self, task: AgentTaskRequest) -> AgentResult: ...

    async def cancel(self, task: AgentTaskRequest) -> AgentResult: ...

    async def resume(self, task: AgentTaskRequest, checkpoint: AgentCheckpoint) -> AgentResult: ...


class ReferenceCheckpointAdapter:
    """Deterministic in-process adapter with recoverable checkpoint/resume behavior."""

    def __init__(self, *, recover_once: bool = False) -> None:
        self._recover_once = bool(recover_once)
        self._identity = AgentIdentity(
            agent_id="reference-checkpoint-agent",
            agent_version="1.0.0",
            adapter_id="reference-checkpoint-adapter",
            adapter_version="1.0.0",
            provider_kind="reference",
            declared_work_kinds=("implementation",),
            declared_capabilities=("bounded-source-evidence", "checkpoint-resume"),
            model_runtime_label="deterministic-reference-a",
        )

    def describe(self) -> AgentIdentity:
        return self._identity

    async def invoke(self, task: AgentTaskRequest) -> AgentResult:
        _require_task_for_adapter(task, self._identity)
        raw = {"state": "retry" if self._recover_once else "done", "coverage": list(task.binding.acceptance_ids)}
        if raw["state"] == "retry":
            checkpoint = AgentCheckpoint(
                binding=task.binding,
                agent=self._identity,
                checkpoint_id=f"checkpoint:{task.binding.attempt_id}",
                summary="bounded reference checkpoint",
                evidence_refs=(
                    AgentEvidenceReference(
                        EvidenceKind.CHECKPOINT,
                        f"checkpoint:{task.binding.attempt_id}",
                    ),
                ),
            )
            return AgentResult(
                binding=task.binding,
                agent=self._identity,
                status=AgentLifecycleStatus.RECOVERABLE_FAILURE,
                reason_code="REFERENCE_RECOVERABLE_FAILURE",
                summary="reference adapter requested bounded resume",
                claimed_acceptance_ids=task.binding.acceptance_ids,
                evidence_refs=checkpoint.evidence_refs,
                checkpoint=checkpoint,
            )
        return _reference_success(task, self._identity, shape="mapping")

    async def cancel(self, task: AgentTaskRequest) -> AgentResult:
        _require_task_for_adapter(task, self._identity)
        return AgentResult(
            binding=task.binding,
            agent=self._identity,
            status=AgentLifecycleStatus.REJECTED,
            reason_code="CANCELLATION_UNSUPPORTED",
            summary="reference adapter does not support active cancellation",
        )

    async def resume(self, task: AgentTaskRequest, checkpoint: AgentCheckpoint) -> AgentResult:
        _require_task_for_adapter(task, self._identity)
        decision = verify_checkpoint_admission(expected_task=task, checkpoint=checkpoint)
        if not decision.admitted:
            return AgentResult(
                binding=task.binding,
                agent=self._identity,
                status=AgentLifecycleStatus.REJECTED,
                reason_code=decision.reason.value,
                summary="checkpoint was not admissible for this task",
            )
        return _reference_success(task, self._identity, shape="mapping-resume")


class ReferenceTimeoutAdapter:
    """Deterministic in-process adapter with timeout and cancellation normalization."""

    def __init__(self, *, timeout: bool = False, unknown_failure: bool = False) -> None:
        self._timeout = bool(timeout)
        self._unknown_failure = bool(unknown_failure)
        self._identity = AgentIdentity(
            agent_id="reference-timeout-agent",
            agent_version="2.0.0",
            adapter_id="reference-timeout-adapter",
            adapter_version="1.0.0",
            provider_kind="reference",
            declared_work_kinds=("implementation",),
            declared_capabilities=("bounded-source-evidence", "cancellation"),
            model_runtime_label="deterministic-reference-b",
        )

    def describe(self) -> AgentIdentity:
        return self._identity

    async def invoke(self, task: AgentTaskRequest) -> AgentResult:
        _require_task_for_adapter(task, self._identity)
        raw = ("unknown", None) if self._unknown_failure else (("timeout", None) if self._timeout else ("finished", "ok"))
        state = raw[0]
        if state == "timeout":
            return AgentResult(
                binding=task.binding,
                agent=self._identity,
                status=AgentLifecycleStatus.TIMEOUT,
                reason_code="REFERENCE_TIMEOUT",
                summary="reference adapter normalized a timeout",
                claimed_acceptance_ids=task.binding.acceptance_ids,
                metrics=(
                    MetricObservation(
                        metric=MetricName.DURATION,
                        availability=MetricAvailability.UNKNOWN,
                        source="reference-timeout-adapter",
                    ),
                ),
            )
        if state == "unknown":
            return AgentResult(
                binding=task.binding,
                agent=self._identity,
                status=AgentLifecycleStatus.TERMINAL_FAILURE,
                reason_code="UNKNOWN_PROVIDER_FAILURE",
                summary="reference adapter normalized an unknown provider failure",
            )
        return _reference_success(task, self._identity, shape="tuple")

    async def cancel(self, task: AgentTaskRequest) -> AgentResult:
        _require_task_for_adapter(task, self._identity)
        return AgentResult(
            binding=task.binding,
            agent=self._identity,
            status=AgentLifecycleStatus.CANCELLED,
            reason_code="CANCELLED_BY_PARALLAX",
            summary="reference adapter acknowledged cancellation",
        )

    async def resume(self, task: AgentTaskRequest, checkpoint: AgentCheckpoint) -> AgentResult:
        _require_task_for_adapter(task, self._identity)
        return AgentResult(
            binding=task.binding,
            agent=self._identity,
            status=AgentLifecycleStatus.REJECTED,
            reason_code="RESUME_UNSUPPORTED",
            summary="reference adapter does not support checkpoint resume",
        )


def safe_json(
    value: AgentTaskRequest | AgentResult | AgentCheckpoint | AgentLifecycleEvidence | AdmissionDecision,
) -> str:
    if not isinstance(
        value,
        (AgentTaskRequest, AgentResult, AgentCheckpoint, AgentLifecycleEvidence, AdmissionDecision),
    ):
        raise AgentProtocolError("safe_json requires canonical protocol evidence")
    return json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _reference_success(task: AgentTaskRequest, agent: AgentIdentity, *, shape: str) -> AgentResult:
    metrics = (
        MetricObservation(
            metric=MetricName.DURATION,
            availability=MetricAvailability.OBSERVED,
            source=agent.adapter_id,
            value=1.0,
            unit="seconds",
            provenance_kind=MetricProvenanceKind.PARALLAX,
            provenance_ref=f"observation:{task.binding.request_id}",
        ),
        MetricObservation(
            metric=MetricName.COST,
            availability=MetricAvailability.UNAVAILABLE,
            source=agent.adapter_id,
        ),
    )
    return AgentResult(
        binding=task.binding,
        agent=agent,
        status=AgentLifecycleStatus.COMPLETED,
        reason_code=None,
        summary=f"reference implementation completed via {shape}",
        claimed_acceptance_ids=task.binding.acceptance_ids,
        changed_paths=("src/reference.txt",),
        evidence_refs=(
            AgentEvidenceReference(EvidenceKind.ARTIFACT, f"artifact:{task.binding.request_id}"),
        ),
        metrics=metrics,
    )


def _require_task_for_adapter(task: AgentTaskRequest, identity: AgentIdentity) -> None:
    if not isinstance(task, AgentTaskRequest):
        raise AgentProtocolError("adapter requires AgentTaskRequest")
    if task.agent.digest != identity.digest or task.binding.agent_identity_digest != identity.digest:
        raise AgentProtocolError("task is bound to a different agent/adapter identity")


def _binding_mismatch(expected: AgentTaskBinding, actual: AgentTaskBinding) -> AdmissionReason | None:
    if expected.project_id != actual.project_id:
        return AdmissionReason.PROJECT_MISMATCH
    if expected.run_id != actual.run_id:
        return AdmissionReason.RUN_MISMATCH
    if (
        expected.work_specification_id != actual.work_specification_id
        or expected.work_specification_revision != actual.work_specification_revision
        or expected.work_specification_digest != actual.work_specification_digest
    ):
        return AdmissionReason.WORK_SPECIFICATION_MISMATCH
    if expected.acceptance_ids != actual.acceptance_ids:
        return AdmissionReason.ACCEPTANCE_CONTRACT_MISMATCH
    if expected.operation_id != actual.operation_id:
        return AdmissionReason.OPERATION_MISMATCH
    if expected.request_id != actual.request_id:
        return AdmissionReason.REQUEST_MISMATCH
    if expected.attempt_number != actual.attempt_number or expected.attempt_id != actual.attempt_id:
        return AdmissionReason.ATTEMPT_MISMATCH
    if expected.agent_identity_digest != actual.agent_identity_digest:
        return AdmissionReason.AGENT_IDENTITY_MISMATCH
    if expected.source_context != actual.source_context:
        return AdmissionReason.SOURCE_CONTEXT_MISMATCH
    return None


def _reject(digest: str, reason: AdmissionReason) -> AdmissionDecision:
    return AdmissionDecision(admitted=False, reason=reason, evidence_digest=digest)


def _verify_bound_agent(binding: AgentTaskBinding, agent: AgentIdentity) -> None:
    if not isinstance(binding, AgentTaskBinding) or not isinstance(agent, AgentIdentity):
        raise AgentProtocolError("binding and agent are required canonical values")
    if binding.agent_identity_digest != agent.digest:
        raise AgentProtocolError("evidence agent identity does not match task binding")


def _uuid(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise AgentProtocolError(f"{field} must be UUID string")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise AgentProtocolError(f"{field} must be UUID string") from exc
    if str(parsed) != value.lower():
        value = str(parsed)
    return value


def _sha256(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise AgentProtocolError(f"{field} must be sha256 hex")
    return value


def _token(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise AgentProtocolError(f"{field} must be a bounded lowercase identifier")
    return value


def _version(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise AgentProtocolError(f"{field} must be a bounded version label")
    return value


def _reference(value: str, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > _MAX_REFERENCE_BYTES
        or not _REFERENCE_RE.fullmatch(value)
        or value.lower().startswith(("http:", "https:"))
        or _SENSITIVE_REFERENCE_RE.search(value)
    ):
        raise AgentProtocolError(f"{field} must be a bounded opaque reference")
    return value


def _token_set(values: tuple[str, ...], *, field: str, required: bool = False) -> tuple[str, ...]:
    items = tuple(values)
    if len(items) > _MAX_CAPABILITY_TOKENS:
        raise AgentProtocolError(f"{field} exceeds bounded limit")
    normalized = tuple(sorted(_token(item, field=field) for item in items))
    if len(set(normalized)) != len(normalized):
        raise AgentProtocolError(f"{field} must be unique")
    if required and not normalized:
        raise AgentProtocolError(f"{field} must not be empty")
    return normalized


def _acceptance_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    items = tuple(values)
    if not items or len(items) > _MAX_ACCEPTANCE_IDS:
        raise AgentProtocolError("acceptance_ids must be non-empty and bounded")
    for item in items:
        if not isinstance(item, str) or not _ACCEPTANCE_ID_RE.fullmatch(item):
            raise AgentProtocolError("acceptance_ids contain invalid id")
    if len(set(items)) != len(items):
        raise AgentProtocolError("acceptance_ids must be unique")
    return items


def _evidence_refs(values: tuple[AgentEvidenceReference, ...]) -> tuple[AgentEvidenceReference, ...]:
    items = tuple(values)
    if len(items) > _MAX_CONTEXT_REFS or any(not isinstance(item, AgentEvidenceReference) for item in items):
        raise AgentProtocolError("evidence_refs must contain bounded references")
    if len({(item.kind, item.reference_id, item.digest) for item in items}) != len(items):
        raise AgentProtocolError("evidence_refs must be unique")
    return items


def _safe_summary(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.encode("utf-8")) > _MAX_SUMMARY_BYTES
        or any(ord(char) < 32 and char not in "\t" for char in value)
        or _SENSITIVE_SUMMARY_RE.search(value)
    ):
        raise AgentProtocolError("summary must be bounded and privacy-safe")
    return " ".join(value.split())


def _safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 192:
        raise AgentProtocolError("changed path must be bounded")
    if "\\" in value or value.startswith("/"):
        raise AgentProtocolError("changed path must be a relative POSIX path")
    path = PurePosixPath(value)
    parts = path.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise AgentProtocolError("changed path cannot traverse")
    for part in parts:
        lowered = part.lower()
        if (
            not _SAFE_PATH_PART_RE.fullmatch(part)
            or lowered in _SENSITIVE_PATH_PARTS
            or lowered == ".env"
            or lowered.startswith(".env.")
            or lowered.startswith("credential.")
            or lowered.startswith("credentials.")
            or lowered.startswith("secret.")
            or lowered.startswith("secrets.")
        ):
            raise AgentProtocolError("changed path contains unsafe segment")
    return str(path)


def _aware_utc(value: datetime, *, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AgentProtocolError(f"{field} must be timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _digest(value: dict[str, object]) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(payload).hexdigest()
