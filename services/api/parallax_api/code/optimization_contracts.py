from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re
from typing import Iterable

MAX_GRAPH_NODES = 128
MAX_GRAPH_EDGES = 512
MAX_REFS = 24
MAX_STATE_BYTES = 24_000
MAX_TELEMETRY = 256
MAX_REGISTRY_RECORDS = 128
MAX_STRING = 200
MAX_DURATION_MS = 7 * 24 * 60 * 60 * 1000
_STATE_STAGE = "OPTIMIZATION_STATE"
_STATE_STATUS = "RECORDED"
_STATE_PROGRAM = "optimization-controller-v0.16.4"
_STATE_TOOL = "protected-optimization-controller"
_STATE_KIND = "optimization_state"
_STATE_VERSION = 1

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+*?\[\]-]{0,199}$")
_FORBIDDEN_PREFIXES = (
    "http://",
    "https://",
    "file:",
    "data:",
    "command:",
    "shell:",
    "exec:",
    "subprocess:",
    "env:",
    "environment:",
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|authorization|cookie|password)\s*[:=]\s*\S{6,}"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"(?:vcp|vca|ghp|github_pat)_[A-Za-z0-9._-]{10,}", re.I),
)
_PRIVATE_REASONING_TERMS = (
    "chain_of_thought",
    "chain-of-thought",
    "scratchpad",
    "hidden_reasoning",
    "hidden-reasoning",
    "internal_reasoning",
    "internal-reasoning",
    "rationale_trace",
    "rationale-trace",
)


class OptimizationError(RuntimeError):
    pass


class OptimizationPolicyError(OptimizationError):
    pass


class OptimizationGraphError(OptimizationError):
    pass


class OptimizationStateConflict(OptimizationError):
    pass


class OptimizationWorkerConflict(OptimizationError):
    pass


def _canonical_digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _digest(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise OptimizationPolicyError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _lineage(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _LINEAGE_RE.fullmatch(value):
        raise OptimizationPolicyError(f"{field} must be an immutable source lineage ref")
    return value


def _safe_token(value: str, *, field: str) -> str:
    if not isinstance(value, str):
        raise OptimizationPolicyError(f"{field} must be a string")
    candidate = value.strip()
    lowered = candidate.casefold()
    if not candidate or len(candidate) > MAX_STRING or not _SAFE_TOKEN_RE.fullmatch(candidate):
        raise OptimizationPolicyError(f"{field} is invalid or unbounded")
    if lowered.startswith(_FORBIDDEN_PREFIXES):
        raise OptimizationPolicyError(f"{field} cannot contain executable, network, environment or file authority")
    if any(term in lowered for term in _PRIVATE_REASONING_TERMS):
        raise OptimizationPolicyError(f"{field} cannot contain private reasoning")
    if any(pattern.search(candidate) for pattern in _SECRET_PATTERNS):
        raise OptimizationPolicyError(f"{field} contains secret-bearing material")
    return candidate


def _refs(values: Iterable[str], *, field: str, limit: int = MAX_REFS) -> tuple[str, ...]:
    result = tuple(_safe_token(value, field=field) for value in values)
    if len(result) > limit or len(set(result)) != len(result):
        raise OptimizationPolicyError(f"{field} must be unique and bounded")
    return result


def _repo_path(value: str, *, field: str = "path") -> str:
    if not isinstance(value, str):
        raise OptimizationPolicyError(f"{field} must be a string")
    candidate = value.strip().replace("\\", "/")
    if not candidate or candidate.startswith("/") or len(candidate) > 240:
        raise OptimizationPolicyError(f"{field} must be a bounded repository-relative path")
    path = PurePosixPath(candidate)
    if ".." in path.parts or "." in path.parts:
        raise OptimizationPolicyError(f"{field} cannot escape repository scope")
    lowered = candidate.casefold()
    if any(pattern.search(candidate) for pattern in _SECRET_PATTERNS) or any(term in lowered for term in _PRIVATE_REASONING_TERMS):
        raise OptimizationPolicyError(f"{field} contains protected material")
    return candidate


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise OptimizationPolicyError("timestamp must be datetime")
    if value.tzinfo is None:
        raise OptimizationPolicyError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


class OptimizationNodeKind(StrEnum):
    WORKSTREAM = "WORKSTREAM"
    CONTRACT = "CONTRACT"
    VALIDATION_GATE = "VALIDATION_GATE"
    RELEASE_GATE = "RELEASE_GATE"


class OptimizationNodeState(StrEnum):
    BLOCKED = "BLOCKED"
    READY = "READY"
    RUNNING = "RUNNING"
    READY_FOR_INTEGRATION = "READY_FOR_INTEGRATION"
    PASSED = "PASSED"
    FAILED = "FAILED"


class SafeBoundary(StrEnum):
    BEFORE_MUTATION = "BEFORE_MUTATION"
    AFTER_ACCEPTED_VALIDATION = "AFTER_ACCEPTED_VALIDATION"
    AFTER_RECORDED_SIDE_EFFECT = "AFTER_RECORDED_SIDE_EFFECT"
    UNSAFE = "UNSAFE"


class ValidationBoundary(StrEnum):
    DEVELOPMENT_FAST = "DEVELOPMENT_FAST"
    WORKER_ACCEPTANCE = "WORKER_ACCEPTANCE"
    INTEGRATION_ACCEPTANCE = "INTEGRATION_ACCEPTANCE"
    RELEASE_PROMOTION = "RELEASE_PROMOTION"


class CancellationAction(StrEnum):
    WAIT = "WAIT"
    CANCEL_AT_CHECKPOINT = "CANCEL_AT_CHECKPOINT"
    SUPERSEDE_AT_CHECKPOINT = "SUPERSEDE_AT_CHECKPOINT"


class ModelClass(StrEnum):
    FAST = "FAST"
    GENERAL = "GENERAL"
    DEEP = "DEEP"


class PreflightFindingKind(StrEnum):
    GRAPH = "GRAPH"
    CONTRADICTION = "CONTRADICTION"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    UNTESTABLE_ACCEPTANCE = "UNTESTABLE_ACCEPTANCE"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    ARCHITECTURE_CONFLICT = "ARCHITECTURE_CONFLICT"
    CONSTITUTION_CONFLICT = "CONSTITUTION_CONFLICT"
    ACCEPTANCE_OWNERSHIP = "ACCEPTANCE_OWNERSHIP"


class DevelopmentPhase(StrEnum):
    QUEUE = "QUEUE"
    PLANNING = "PLANNING"
    GENERATION = "GENERATION"
    ENVIRONMENT = "ENVIRONMENT"
    BUILD = "BUILD"
    TEST = "TEST"
    BROWSER = "BROWSER"
    VISUAL = "VISUAL"
    PROVIDER = "PROVIDER"
    RETRY = "RETRY"
    INTEGRATION = "INTEGRATION"
    STALL = "STALL"
    HUMAN_WAIT = "HUMAN_WAIT"
