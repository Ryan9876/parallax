from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import json

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from ..models import EngineeringAttempt, EngineeringRun, utcnow
from ..repositories.engineering_runs import EngineeringRunRepository
from .optimization_contracts import (
    MAX_STATE_BYTES, OptimizationStateConflict, _PRIVATE_REASONING_TERMS, _SECRET_PATTERNS,
    _digest, _refs, _safe_token, _utc,
)
from .optimization_graph import DependencyGraph

_STATE_STAGE = "OPTIMIZATION_STATE"
_STATE_STATUS = "RECORDED"
_STATE_PROGRAM = "optimization-controller-v0.16.4"
_STATE_TOOL = "protected-optimization-controller"
_STATE_KIND = "optimization_state"
_STATE_VERSION = 1

@dataclass(frozen=True, slots=True)
class OptimizationState:
    session_id: str
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    graph: DependencyGraph
    evidence_refs: tuple[str, ...]
    updated_at: datetime
    revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_id", _safe_token(self.session_id, field="session_id"))
        object.__setattr__(self, "project_id", _safe_token(self.project_id, field="project_id"))
        object.__setattr__(self, "run_id", _safe_token(self.run_id, field="run_id"))
        object.__setattr__(self, "work_specification_id", _safe_token(self.work_specification_id, field="work_specification_id"))
        _digest(self.work_specification_digest, field="work_specification_digest")
        if self.graph.project_id != self.project_id:
            raise OptimizationStateConflict("optimization graph Project binding mismatch")
        if not isinstance(self.work_specification_revision, int) or self.work_specification_revision < 0:
            raise OptimizationStateConflict("Work Specification revision must be nonnegative")
        if not isinstance(self.revision, int) or self.revision < 0:
            raise OptimizationStateConflict("optimization state revision must be nonnegative")
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="optimization_evidence"))
        object.__setattr__(self, "updated_at", _utc(self.updated_at))

    def to_record(self) -> dict[str, object]:
        return {
            "record_kind": _STATE_KIND,
            "record_version": _STATE_VERSION,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "graph": self.graph.to_record(),
            "graph_digest": self.graph.digest,
            "evidence_refs": list(self.evidence_refs),
            "updated_at": self.updated_at.isoformat(),
            "revision": self.revision,
        }

    @classmethod
    def from_record(cls, value: object) -> "OptimizationState":
        if not isinstance(value, dict) or value.get("record_kind") != _STATE_KIND or value.get("record_version") != _STATE_VERSION:
            raise OptimizationStateConflict("stored optimization state version is invalid")
        try:
            graph = DependencyGraph.from_record(value["graph"])
            if graph.digest != value["graph_digest"]:
                raise OptimizationStateConflict("stored optimization graph digest mismatch")
            updated = datetime.fromisoformat(value["updated_at"])
            return cls(
                session_id=value["session_id"],
                project_id=value["project_id"],
                run_id=value["run_id"],
                work_specification_id=value["work_specification_id"],
                work_specification_revision=value["work_specification_revision"],
                work_specification_digest=value["work_specification_digest"],
                graph=graph,
                evidence_refs=tuple(value.get("evidence_refs", ())),
                updated_at=updated,
                revision=value["revision"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OptimizationStateConflict("stored optimization state is invalid") from exc


class EngineeringAttemptOptimizationStateStore:
    """Durable optimization snapshot using the existing bounded EngineeringAttempt ledger."""

    def __init__(self, repository: EngineeringRunRepository) -> None:
        if not isinstance(repository, EngineeringRunRepository):
            raise TypeError("repository must be EngineeringRunRepository")
        self.repository = repository

    @staticmethod
    def operation_key(session_id: str) -> str:
        return f"optimization-state:{_safe_token(session_id, field='session_id')}"

    @staticmethod
    def _encode(state: OptimizationState) -> str:
        encoded = json.dumps(state.to_record(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
            raise OptimizationStateConflict("durable optimization state exceeds protected 24KB bound")
        if any(pattern.search(encoded) for pattern in _SECRET_PATTERNS) or any(term in encoded.casefold() for term in _PRIVATE_REASONING_TERMS):
            raise OptimizationStateConflict("durable optimization state contains protected material")
        return encoded

    def load(self, *, run_id: str, session_id: str) -> OptimizationState | None:
        attempt = self.repository.find_operation(run_id, self.operation_key(session_id))
        if attempt is None:
            return None
        if attempt.stage != _STATE_STAGE or attempt.status != _STATE_STATUS:
            raise OptimizationStateConflict("durable optimization attempt has invalid record type")
        try:
            payload = json.loads(attempt.evidence_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise OptimizationStateConflict("durable optimization evidence is invalid") from exc
        state = OptimizationState.from_record(payload)
        if state.run_id != run_id or state.session_id != session_id:
            raise OptimizationStateConflict("durable optimization identity mismatch")
        self._encode(state)
        return state

    def save(self, *, run: EngineeringRun, state: OptimizationState, expected_revision: int) -> OptimizationState:
        if state.project_id != run.project_id or state.run_id != run.id:
            raise OptimizationStateConflict("optimization state does not match canonical Engineering Run")
        if (
            state.work_specification_id != run.work_specification_id
            or state.work_specification_revision != run.work_specification_revision
            or state.work_specification_digest != run.work_specification_digest
        ):
            raise OptimizationStateConflict("optimization state Work Specification binding mismatch")
        current = self.load(run_id=run.id, session_id=state.session_id)
        if current is None:
            if expected_revision != 0 or state.revision != 0:
                raise OptimizationStateConflict("new optimization state revision mismatch")
            saved = replace(state, revision=1)
            encoded = self._encode(saved)
            attempt = EngineeringAttempt(
                run_id=run.id,
                stage=_STATE_STAGE,
                attempt_number=self.repository._next_attempt_number(run.id, _STATE_STAGE),
                operation_key=self.operation_key(state.session_id),
                status=_STATE_STATUS,
                program_id=_STATE_PROGRAM,
                tool_id=_STATE_TOOL,
                evidence_json=encoded,
                completed_at=utcnow(),
            )
            try:
                self.repository.session.add(attempt)
                self.repository.session.commit()
            except IntegrityError as exc:
                self.repository.session.rollback()
                replay = self.load(run_id=run.id, session_id=state.session_id)
                if replay is None:
                    raise OptimizationStateConflict("concurrent optimization-state creation conflicted") from exc
                return replay
            return saved

        if current.revision != expected_revision or state.revision != expected_revision:
            raise OptimizationStateConflict("optimization state compare-and-swap revision mismatch")
        saved = replace(state, revision=expected_revision + 1)
        encoded = self._encode(saved)
        attempt = self.repository.find_operation(run.id, self.operation_key(state.session_id))
        if attempt is None:
            raise OptimizationStateConflict("durable optimization state disappeared during update")
        old_encoded = attempt.evidence_json
        result = self.repository.session.execute(
            update(EngineeringAttempt)
            .where(EngineeringAttempt.id == attempt.id, EngineeringAttempt.evidence_json == old_encoded)
            .values(evidence_json=encoded, completed_at=utcnow())
        )
        if result.rowcount != 1:
            self.repository.session.rollback()
            raise OptimizationStateConflict("concurrent optimization-state update conflicted")
        self.repository.session.commit()
        return saved
