from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff
from hashlib import sha256
import json
import re
from typing import Literal

from ..evaluation.security import security_findings
from ..models import EngineeringAttempt, EngineeringRun
from ..repositories.run_events import RunEventRepository
from .domain import WorkflowStage
from .run_events import RunEvent
from .service import EngineeringRunService
from .workspace_lineage import (
    ProjectRunIdentity,
    SourceLineage,
    SourceLineageStore,
    SourcePolicyError,
    WorkspaceLineageError,
)


MAX_CURSOR = 9_223_372_036_854_775_807
MAX_EVENT_PAGE = 200
MAX_TREE_PAGE = 200
MAX_SOURCE_TEXT_BYTES = 256 * 1024
MAX_DIFF_FILES = 80
MAX_DIFF_TEXT_FILE_BYTES = 128 * 1024
MAX_DIFF_OUTPUT_BYTES = 512 * 1024
MAX_EVIDENCE_EXCERPT = 2_000
MAX_EVIDENCE_LIST = 64

_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}$")

_ALLOWED_EXECUTION_EVIDENCE = frozenset(
    {
        "source_lineage_ref",
        "source_content_digest",
        "tool_id",
        "invocation_digest",
        "exit_code",
        "duration_ms",
        "stdout_digest",
        "stdout_excerpt",
        "stderr_digest",
        "stderr_excerpt",
        "timed_out",
        "redacted",
        "protected_success",
        "executor",
        "network_policy",
        "lineage_source_transfer",
        "source_file_count",
        "source_total_bytes",
        "fresh_repository_checkout",
        "git_source",
        "lineage_cleanup_failed",
        "acceptance_ids",
        "acceptance_ids_covered",
        "acceptance_ids_targeted",
        "acceptance_ids_verified",
    }
)


class ProtectedObservationError(RuntimeError):
    pass


class ProtectedObservationNotFound(LookupError, ProtectedObservationError):
    pass


class ProtectedObservationUnavailable(ProtectedObservationError):
    pass


class ProtectedObservationValidation(ValueError, ProtectedObservationError):
    pass


@dataclass(frozen=True, slots=True)
class ScopedRun:
    run: EngineeringRun
    identity: ProjectRunIdentity


def resolve_event_cursor(*, after_sequence: int, last_event_id: str | None) -> int:
    if not isinstance(after_sequence, int) or isinstance(after_sequence, bool):
        raise ProtectedObservationValidation("after_sequence must be a nonnegative integer")
    if after_sequence < 0 or after_sequence > MAX_CURSOR:
        raise ProtectedObservationValidation("after_sequence is outside the protected cursor bound")
    if last_event_id is None:
        return after_sequence
    if not isinstance(last_event_id, str) or not re.fullmatch(r"[1-9][0-9]{0,18}", last_event_id):
        raise ProtectedObservationValidation("Last-Event-ID must be a positive durable event sequence")
    value = int(last_event_id)
    if value > MAX_CURSOR:
        raise ProtectedObservationValidation("Last-Event-ID is outside the protected cursor bound")
    return value


def public_event(event: RunEvent) -> dict[str, object]:
    append = event.append
    return {
        "id": event.id,
        "project_id": append.project_id,
        "run_id": append.run_id,
        "sequence": event.sequence,
        "event_key": append.event_key,
        "event_type": append.event_type.value,
        "stage": append.stage,
        "outcome": append.outcome.value,
        "subsystem": append.subsystem.value,
        "attempt_id": append.attempt_id,
        "worker_execution_id": append.worker_execution_id,
        "source_lineage_ref": append.source_lineage_ref,
        "parent_source_lineage_ref": append.parent_source_lineage_ref,
        "operation_ref": append.operation_ref,
        "artifact_ref": append.artifact_ref,
        "evidence_ref": append.evidence_ref,
        "failure_code": append.failure_code,
        "summary": append.summary,
        "metadata": dict(append.metadata),
        "occurred_at": append.occurred_at,
        "created_at": event.created_at,
    }


def _safe_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _SAFE_IDENTIFIER_RE.fullmatch(value) is None:
        return None
    if security_findings({"value": value}):
        return None
    return value


def _safe_excerpt(value: object) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    candidate = value[:MAX_EVIDENCE_EXCERPT]
    truncated = len(candidate) != len(value)
    if security_findings({"excerpt": candidate}):
        return "[REDACTED]", True
    return candidate, truncated


def _safe_evidence_value(key: str, value: object) -> object | None:
    if key in {"stdout_excerpt", "stderr_excerpt"}:
        return _safe_excerpt(value)[0]
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) > 240 or security_findings({key: value}):
            return None
        if key in {"source_lineage_ref"} and _LINEAGE_RE.fullmatch(value) is None:
            return None
        if key in {"source_content_digest", "invocation_digest", "stdout_digest", "stderr_digest"}:
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                return None
        return value
    if isinstance(value, list):
        if len(value) > MAX_EVIDENCE_LIST:
            return None
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or len(item) > 160 or security_findings({key: item}):
                return None
            normalized.append(item)
        return normalized
    return None


class EngineeringObservabilityService:
    """Read-only projection for Wave 4 Live Build.

    Engineering Run, attempt, worker, source-lineage, provider and evaluation
    records remain authoritative. This service has no mutation or execution
    method and never accepts caller-supplied Project authority.
    """

    def __init__(
        self,
        run_service: EngineeringRunService,
        event_repository: RunEventRepository,
        *,
        lineage_store: SourceLineageStore | None = None,
    ) -> None:
        self.run_service = run_service
        self.event_repository = event_repository
        self.lineage_store = lineage_store

    def _scope(self, run_id: str) -> ScopedRun:
        run = self.run_service.get(run_id)
        if not run.project_id:
            raise ProtectedObservationNotFound("protected run observability is unavailable")
        try:
            identity = ProjectRunIdentity(project_id=run.project_id, run_id=run.id)
        except (TypeError, ValueError, RuntimeError) as exc:
            raise ProtectedObservationNotFound("protected run observability is unavailable") from exc
        return ScopedRun(run=run, identity=identity)

    def event_page(self, *, run_id: str, after_sequence: int = 0, limit: int = 100) -> dict[str, object]:
        scope = self._scope(run_id)
        if not isinstance(after_sequence, int) or isinstance(after_sequence, bool) or not 0 <= after_sequence <= MAX_CURSOR:
            raise ProtectedObservationValidation("after_sequence is outside the protected cursor bound")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_EVENT_PAGE:
            raise ProtectedObservationValidation(f"event limit must be between 1 and {MAX_EVENT_PAGE}")
        try:
            events = self.event_repository.list_for_run(
                project_id=scope.identity.project_id,
                run_id=scope.identity.run_id,
                after_sequence=after_sequence,
                limit=limit,
            )
            latest = self.event_repository.latest_sequence(
                project_id=scope.identity.project_id,
                run_id=scope.identity.run_id,
            )
        except Exception as exc:
            raise ProtectedObservationUnavailable("durable run-event replay is unavailable") from exc
        next_cursor = events[-1].sequence if events else after_sequence
        return {
            "events": [public_event(event) for event in events],
            "next_after_sequence": next_cursor,
            "has_more": latest > next_cursor,
        }

    def _require_lineage_store(self) -> SourceLineageStore:
        if self.lineage_store is None:
            raise ProtectedObservationUnavailable("durable source-lineage reads are unavailable")
        return self.lineage_store

    def _lineage(self, scope: ScopedRun, lineage_id: str) -> SourceLineage:
        if not isinstance(lineage_id, str) or _LINEAGE_RE.fullmatch(lineage_id) is None:
            raise ProtectedObservationValidation("source lineage identity is invalid")
        store = self._require_lineage_store()
        try:
            return store.resolve(scope.identity, lineage_id)
        except WorkspaceLineageError as exc:
            # Normalize missing, foreign and unverifiable lineage identities to
            # one protected posture after the owner-scoped run is resolved.
            raise ProtectedObservationNotFound("protected source reference is unavailable") from exc
        except Exception as exc:
            raise ProtectedObservationUnavailable("durable source-lineage read failed") from exc

    def source_tree(
        self,
        *,
        run_id: str,
        lineage_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, object]:
        scope = self._scope(run_id)
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ProtectedObservationValidation("tree offset must be a nonnegative integer")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_TREE_PAGE:
            raise ProtectedObservationValidation(f"tree limit must be between 1 and {MAX_TREE_PAGE}")
        lineage = self._lineage(scope, lineage_id)
        page = lineage.files[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "project_id": scope.identity.project_id,
            "run_id": scope.identity.run_id,
            "lineage_id": lineage.lineage_id,
            "parent_lineage_id": lineage.parent_lineage_id,
            "content_digest": lineage.content_digest,
            "source_kind": lineage.source_kind,
            "file_count": lineage.file_count,
            "total_bytes": lineage.total_bytes,
            "files": [item.as_dict() for item in page],
            "next_offset": next_offset,
            "has_more": next_offset < lineage.file_count,
        }

    @staticmethod
    def _entry(lineage: SourceLineage, path: str):
        for entry in lineage.files:
            if entry.path == path:
                return entry
        raise ProtectedObservationNotFound("protected source path is unavailable")

    def _normalize_path(self, path: str) -> str:
        store = self._require_lineage_store()
        try:
            # Reuse the canonical lineage policy rather than creating a second
            # path/secret policy for the observer surface.
            return store._normalize_source_path(path)  # noqa: SLF001
        except SourcePolicyError as exc:
            raise ProtectedObservationNotFound("protected source path is unavailable") from exc

    def _read_verified_bytes(self, entry) -> bytes:
        store = self._require_lineage_store()
        try:
            payload = bytes(store.object_store.get(entry.sha256))
        except Exception as exc:
            raise ProtectedObservationUnavailable("immutable source object is unavailable") from exc
        if len(payload) != entry.size or sha256(payload).hexdigest() != entry.sha256:
            raise ProtectedObservationUnavailable("immutable source object failed integrity verification")
        return payload

    @staticmethod
    def _text_availability(payload: bytes, *, ceiling: int) -> tuple[Literal["TEXT", "BINARY", "TOO_LARGE"], str | None]:
        if len(payload) > ceiling:
            return "TOO_LARGE", None
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            return "BINARY", None
        if "\x00" in text:
            return "BINARY", None
        return "TEXT", text

    def source_file(self, *, run_id: str, lineage_id: str, path: str) -> dict[str, object]:
        scope = self._scope(run_id)
        normalized = self._normalize_path(path)
        lineage = self._lineage(scope, lineage_id)
        entry = self._entry(lineage, normalized)
        if entry.size > MAX_SOURCE_TEXT_BYTES:
            return {
                "project_id": scope.identity.project_id,
                "run_id": scope.identity.run_id,
                "lineage_id": lineage.lineage_id,
                "path": entry.path,
                "sha256": entry.sha256,
                "size": entry.size,
                "availability": "TOO_LARGE",
                "text": None,
            }
        payload = self._read_verified_bytes(entry)
        availability, text = self._text_availability(payload, ceiling=MAX_SOURCE_TEXT_BYTES)
        return {
            "project_id": scope.identity.project_id,
            "run_id": scope.identity.run_id,
            "lineage_id": lineage.lineage_id,
            "path": entry.path,
            "sha256": entry.sha256,
            "size": entry.size,
            "availability": availability,
            "text": text,
        }

    def _diff_text(self, *, path: str, before: bytes | None, after: bytes | None) -> tuple[str | None, str, bool]:
        before_text: str | None = None
        after_text: str | None = None
        if before is not None:
            availability, before_text = self._text_availability(before, ceiling=MAX_DIFF_TEXT_FILE_BYTES)
            if availability != "TEXT":
                return None, availability, False
        if after is not None:
            availability, after_text = self._text_availability(after, ceiling=MAX_DIFF_TEXT_FILE_BYTES)
            if availability != "TEXT":
                return None, availability, False
        before_lines = [] if before_text is None else before_text.splitlines()
        after_lines = [] if after_text is None else after_text.splitlines()
        rendered = "\n".join(
            unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        if rendered:
            rendered += "\n"
        encoded = rendered.encode("utf-8")
        if len(encoded) <= MAX_DIFF_OUTPUT_BYTES:
            return rendered, "TEXT", False
        clipped = encoded[:MAX_DIFF_OUTPUT_BYTES].decode("utf-8", errors="ignore")
        return clipped, "TEXT", True

    def source_diff(self, *, run_id: str, from_lineage: str, to_lineage: str) -> dict[str, object]:
        scope = self._scope(run_id)
        before = self._lineage(scope, from_lineage)
        after = self._lineage(scope, to_lineage)
        before_map = {item.path: item for item in before.files}
        after_map = {item.path: item for item in after.files}
        all_paths = sorted(set(before_map) | set(after_map))
        changed_paths = [
            path
            for path in all_paths
            if path not in before_map
            or path not in after_map
            or before_map[path].sha256 != after_map[path].sha256
            or before_map[path].size != after_map[path].size
        ]
        unchanged_count = len(all_paths) - len(changed_paths)
        truncated = len(changed_paths) > MAX_DIFF_FILES
        output_used = 0
        files: list[dict[str, object]] = []

        for path in changed_paths[:MAX_DIFF_FILES]:
            old = before_map.get(path)
            new = after_map.get(path)
            change_type = "ADDED" if old is None else "REMOVED" if new is None else "MODIFIED"
            old_bytes = self._read_verified_bytes(old) if old is not None and old.size <= MAX_DIFF_TEXT_FILE_BYTES else None
            new_bytes = self._read_verified_bytes(new) if new is not None and new.size <= MAX_DIFF_TEXT_FILE_BYTES else None
            if (old is not None and old.size > MAX_DIFF_TEXT_FILE_BYTES) or (
                new is not None and new.size > MAX_DIFF_TEXT_FILE_BYTES
            ):
                diff_text = None
                availability = "TOO_LARGE"
                file_truncated = False
            else:
                diff_text, availability, file_truncated = self._diff_text(
                    path=path,
                    before=old_bytes,
                    after=new_bytes,
                )
            if diff_text is not None:
                encoded = diff_text.encode("utf-8")
                remaining = max(0, MAX_DIFF_OUTPUT_BYTES - output_used)
                if len(encoded) > remaining:
                    diff_text = encoded[:remaining].decode("utf-8", errors="ignore")
                    file_truncated = True
                output_used += len(diff_text.encode("utf-8"))
            truncated = truncated or file_truncated
            files.append(
                {
                    "path": path,
                    "change_type": change_type,
                    "from_sha256": old.sha256 if old else None,
                    "from_size": old.size if old else None,
                    "to_sha256": new.sha256 if new else None,
                    "to_size": new.size if new else None,
                    "availability": availability,
                    "diff_text": diff_text,
                    "truncated": file_truncated,
                }
            )
            if output_used >= MAX_DIFF_OUTPUT_BYTES:
                truncated = truncated or len(files) < len(changed_paths)
                break

        return {
            "project_id": scope.identity.project_id,
            "run_id": scope.identity.run_id,
            "from_lineage": before.lineage_id,
            "to_lineage": after.lineage_id,
            "unchanged_count": unchanged_count,
            "changed_count": len(changed_paths),
            "files": files,
            "truncated": truncated,
        }

    def _attempt(self, scope: ScopedRun, attempt_id: str) -> EngineeringAttempt:
        for attempt in scope.run.attempts:
            if attempt.id == attempt_id:
                return attempt
        raise ProtectedObservationNotFound("protected attempt evidence is unavailable")

    def attempt_evidence(self, *, run_id: str, attempt_id: str) -> dict[str, object]:
        scope = self._scope(run_id)
        attempt = self._attempt(scope, attempt_id)
        if attempt.stage not in {
            WorkflowStage.BUILD.value,
            WorkflowStage.TEST.value,
            WorkflowStage.VERIFY.value,
        }:
            raise ProtectedObservationValidation("only protected BUILD/TEST/VERIFY evidence is observable here")
        try:
            raw = json.loads(attempt.evidence_json or "{}")
        except json.JSONDecodeError:
            raw = None
        availability = "AVAILABLE" if isinstance(raw, dict) else "UNAVAILABLE"
        evidence: dict[str, object] = {}
        redacted = False
        if isinstance(raw, dict):
            for key in _ALLOWED_EXECUTION_EVIDENCE:
                if key not in raw:
                    continue
                value = _safe_evidence_value(key, raw[key])
                if value is not None:
                    evidence[key] = value
                elif raw[key] is not None:
                    redacted = True
            for excerpt_key in ("stdout_excerpt", "stderr_excerpt"):
                if excerpt_key in raw:
                    value, excerpt_redacted = _safe_excerpt(raw[excerpt_key])
                    if value is not None:
                        evidence[excerpt_key] = value
                    redacted = redacted or excerpt_redacted
            if redacted:
                evidence["redacted"] = True
            if security_findings(evidence):
                evidence = {"redacted": True}
                availability = "REDACTED"

        return {
            "project_id": scope.identity.project_id,
            "run_id": scope.identity.run_id,
            "attempt_id": attempt.id,
            "stage": attempt.stage,
            "attempt_number": attempt.attempt_number,
            "status": attempt.status,
            "program_id": _safe_identifier(attempt.program_id),
            "model_id": _safe_identifier(attempt.model_id),
            "tool_id": _safe_identifier(attempt.tool_id),
            "failure_code": attempt.failure_code,
            "started_at": attempt.started_at,
            "completed_at": attempt.completed_at,
            "availability": availability,
            "evidence": evidence,
        }


__all__ = [
    "EngineeringObservabilityService",
    "MAX_CURSOR",
    "MAX_DIFF_FILES",
    "MAX_DIFF_OUTPUT_BYTES",
    "MAX_EVENT_PAGE",
    "MAX_SOURCE_TEXT_BYTES",
    "MAX_TREE_PAGE",
    "ProtectedObservationError",
    "ProtectedObservationNotFound",
    "ProtectedObservationUnavailable",
    "ProtectedObservationValidation",
    "public_event",
    "resolve_event_cursor",
]
