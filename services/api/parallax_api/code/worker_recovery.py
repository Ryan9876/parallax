from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import EngineeringRun
    from ..repositories.worker_executions import EngineeringWorkerExecution, WorkerExecutionRepository


MAX_CHECKPOINT_JSON = 12_000
MAX_REF_ITEMS = 16
MAX_REF_LENGTH = 240
MAX_BLOCKER_LENGTH = 120
DEFAULT_LEASE_SECONDS = 120
MIN_LEASE_SECONDS = 5
MAX_LEASE_SECONDS = 900
DEFAULT_MAX_RETRIES = 5
DEFAULT_MAX_NO_PROGRESS = 3
DEFAULT_MAX_OSCILLATIONS = 2

_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_STEP_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,239}$")
_FORBIDDEN_REF_PREFIXES = ("http://", "https://", "data:", "file:")
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|authorization|cookie|password)\s*[:=]\s*\S{8,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?:vcp|vca|ghp|github_pat)_[A-Za-z0-9._-]{12,}", flags=re.I),
)


class WorkerLifecycleState(StrEnum):
    RUNNING = "RUNNING"
    PROGRESSING = "PROGRESSING"
    CHECKPOINTED = "CHECKPOINTED"
    STALLED = "STALLED"
    RECOVERING = "RECOVERING"
    REASSIGNED = "REASSIGNED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    READY_FOR_INTEGRATION = "READY_FOR_INTEGRATION"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class StallClassification(StrEnum):
    PROCESS_LOSS = "PROCESS_LOSS"
    TEST_CI_HANG = "TEST_CI_HANG"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    DEPENDENCY_WAIT = "DEPENDENCY_WAIT"
    RATE_LIMIT = "RATE_LIMIT"
    CREDENTIAL_AUTHORIZATION = "CREDENTIAL_AUTHORIZATION"
    CONTENTION_DEADLOCK = "CONTENTION_DEADLOCK"
    REPEATED_IMPLEMENTATION_FAILURE = "REPEATED_IMPLEMENTATION_FAILURE"
    HUMAN_AUTHORITY_SPECIFICATION = "HUMAN_AUTHORITY_SPECIFICATION"
    UNKNOWN = "UNKNOWN"


class RecoveryAction(StrEnum):
    REASSIGN = "REASSIGN"
    RETRY = "RETRY"
    BACKOFF_RETRY = "BACKOFF_RETRY"
    WAIT_DEPENDENCY = "WAIT_DEPENDENCY"
    REFRESH_CREDENTIAL = "REFRESH_CREDENTIAL"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    STOP_BOUNDED = "STOP_BOUNDED"


TERMINAL_STATES = {WorkerLifecycleState.SUCCEEDED, WorkerLifecycleState.FAILED}


class WorkerRecoveryError(RuntimeError):
    pass


class WorkerLeaseConflict(WorkerRecoveryError):
    pass


class WorkerLeaseExpired(WorkerRecoveryError):
    pass


class WorkerStaleLease(WorkerRecoveryError):
    pass


class WorkerCheckpointError(WorkerRecoveryError):
    pass


@dataclass(frozen=True, slots=True)
class WorkerLease:
    execution_id: str
    run_id: str
    owner_id: str
    generation: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class WorkerCheckpoint:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    plan_ref: str
    current_step: str
    source_lineage_ref: str | None = None
    last_known_good_lineage_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    blocker_code: str | None = None

    def payload(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "plan_ref": self.plan_ref,
            "current_step": self.current_step,
            "source_lineage_ref": self.source_lineage_ref,
            "last_known_good_lineage_ref": self.last_known_good_lineage_ref,
            "evidence_refs": list(self.evidence_refs),
            "dependencies": list(self.dependencies),
            "blocker_code": self.blocker_code,
        }


@dataclass(frozen=True, slots=True)
class WorkerStallEvidence:
    process_lost: bool = False
    test_or_ci_hung: bool = False
    provider_unavailable: bool = False
    dependency_wait: bool = False
    rate_limited: bool = False
    credential_failure: bool = False
    credential_refreshable: bool = False
    contention_or_deadlock: bool = False
    repeated_implementation_failure: bool = False
    human_approval_required: bool = False
    material_specification_ambiguity: bool = False


@dataclass(frozen=True, slots=True)
class WorkerStallDecision:
    classification: StallClassification
    action: RecoveryAction
    human_required: bool


@dataclass(frozen=True, slots=True)
class WorkerHealthSnapshot:
    execution_id: str
    run_id: str
    state: WorkerLifecycleState
    lease_status: str
    lease_generation: int
    current_step: str | None
    source_lineage_ref: str | None
    last_known_good_lineage_ref: str | None
    checkpoint_revision: int
    last_meaningful_progress_at: datetime | None
    retry_count: int
    no_progress_count: int
    oscillation_count: int
    stall_classification: StallClassification | None
    blocker_code: str | None
    dependencies: tuple[str, ...]
    next_recovery_action: RecoveryAction | None
    human_required: bool


@dataclass(frozen=True, slots=True)
class WorkerProgressResult:
    execution: "EngineeringWorkerExecution"
    meaningful_progress: bool
    bounded_stop: bool


def _validate_ref(value: str, *, field: str) -> str:
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_REF_LENGTH or not _SAFE_REF_RE.fullmatch(candidate):
        raise WorkerCheckpointError(f"{field} is invalid")
    lowered = candidate.casefold()
    if lowered.startswith(_FORBIDDEN_REF_PREFIXES):
        raise WorkerCheckpointError(f"{field} cannot contain an arbitrary URL or file reference")
    if any(pattern.search(candidate) for pattern in _SECRET_PATTERNS):
        raise WorkerCheckpointError(f"{field} contains secret-bearing material")
    return candidate


def _validate_lineage(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    if not _LINEAGE_RE.fullmatch(value):
        raise WorkerCheckpointError(f"{field} is not a canonical source lineage reference")
    return value


def _validate_refs(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if len(values) > MAX_REF_ITEMS:
        raise WorkerCheckpointError(f"{field} exceeds protected item bound")
    normalized = tuple(_validate_ref(item, field=field) for item in values)
    if len(set(normalized)) != len(normalized):
        raise WorkerCheckpointError(f"{field} must not contain duplicates")
    return normalized


def validate_checkpoint(run: "EngineeringRun", checkpoint: WorkerCheckpoint, *, existing_plan_ref: str | None) -> dict[str, object]:
    if not run.project_id:
        raise WorkerCheckpointError("worker checkpoint requires a Project-bound Engineering Run")
    if checkpoint.project_id != run.project_id or checkpoint.run_id != run.id:
        raise WorkerCheckpointError("worker checkpoint Project/run identity mismatch")
    if (
        checkpoint.work_specification_id != run.work_specification_id
        or checkpoint.work_specification_revision != run.work_specification_revision
        or checkpoint.work_specification_digest != run.work_specification_digest
    ):
        raise WorkerCheckpointError("worker checkpoint Work Specification binding mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", checkpoint.work_specification_digest or ""):
        raise WorkerCheckpointError("worker checkpoint Work Specification digest is invalid")

    plan_ref = _validate_ref(checkpoint.plan_ref, field="plan_ref")
    if existing_plan_ref is not None and plan_ref != existing_plan_ref:
        raise WorkerCheckpointError("worker checkpoint plan reference cannot change after acceptance")
    if not _STEP_RE.fullmatch(checkpoint.current_step):
        raise WorkerCheckpointError("worker checkpoint current step is invalid")

    evidence_refs = _validate_refs(checkpoint.evidence_refs, field="evidence_refs")
    dependencies = _validate_refs(checkpoint.dependencies, field="dependencies")
    blocker_code = None
    if checkpoint.blocker_code is not None:
        blocker_code = _validate_ref(checkpoint.blocker_code, field="blocker_code")
        if len(blocker_code) > MAX_BLOCKER_LENGTH:
            raise WorkerCheckpointError("blocker_code exceeds protected bound")

    payload = {
        **checkpoint.payload(),
        "plan_ref": plan_ref,
        "source_lineage_ref": _validate_lineage(checkpoint.source_lineage_ref, field="source_lineage_ref"),
        "last_known_good_lineage_ref": _validate_lineage(
            checkpoint.last_known_good_lineage_ref,
            field="last_known_good_lineage_ref",
        ),
        "evidence_refs": list(evidence_refs),
        "dependencies": list(dependencies),
        "blocker_code": blocker_code,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len(serialized) > MAX_CHECKPOINT_JSON:
        raise WorkerCheckpointError("worker checkpoint exceeds protected JSON bound")
    if any(pattern.search(serialized) for pattern in _SECRET_PATTERNS):
        raise WorkerCheckpointError("worker checkpoint contains secret-bearing material")
    return payload


def progress_fingerprint(payload: dict[str, object]) -> str:
    projection = {
        "current_step": payload.get("current_step"),
        "source_lineage_ref": payload.get("source_lineage_ref"),
        "last_known_good_lineage_ref": payload.get("last_known_good_lineage_ref"),
        "evidence_refs": payload.get("evidence_refs") or [],
        "dependencies": payload.get("dependencies") or [],
        "blocker_code": payload.get("blocker_code"),
    }
    return sha256(json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def classify_stall(evidence: WorkerStallEvidence) -> WorkerStallDecision:
    if evidence.human_approval_required or evidence.material_specification_ambiguity:
        return WorkerStallDecision(
            StallClassification.HUMAN_AUTHORITY_SPECIFICATION,
            RecoveryAction.HUMAN_REQUIRED,
            True,
        )
    if evidence.credential_failure:
        return WorkerStallDecision(
            StallClassification.CREDENTIAL_AUTHORIZATION,
            RecoveryAction.REFRESH_CREDENTIAL if evidence.credential_refreshable else RecoveryAction.HUMAN_REQUIRED,
            not evidence.credential_refreshable,
        )
    if evidence.rate_limited:
        return WorkerStallDecision(StallClassification.RATE_LIMIT, RecoveryAction.BACKOFF_RETRY, False)
    if evidence.provider_unavailable:
        return WorkerStallDecision(StallClassification.PROVIDER_OUTAGE, RecoveryAction.BACKOFF_RETRY, False)
    if evidence.dependency_wait:
        return WorkerStallDecision(StallClassification.DEPENDENCY_WAIT, RecoveryAction.WAIT_DEPENDENCY, False)
    if evidence.test_or_ci_hung:
        return WorkerStallDecision(StallClassification.TEST_CI_HANG, RecoveryAction.RETRY, False)
    if evidence.contention_or_deadlock:
        return WorkerStallDecision(StallClassification.CONTENTION_DEADLOCK, RecoveryAction.BACKOFF_RETRY, False)
    if evidence.repeated_implementation_failure:
        return WorkerStallDecision(
            StallClassification.REPEATED_IMPLEMENTATION_FAILURE,
            RecoveryAction.RETRY,
            False,
        )
    if evidence.process_lost:
        return WorkerStallDecision(StallClassification.PROCESS_LOSS, RecoveryAction.REASSIGN, False)
    return WorkerStallDecision(StallClassification.UNKNOWN, RecoveryAction.STOP_BOUNDED, False)
