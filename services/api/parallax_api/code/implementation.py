from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .patching import PatchError, PreparedPatch, SourcePatch, TextPatchEngine


DEFAULT_MAX_PATCHES = 32
DEFAULT_MAX_TOTAL_SOURCE_BYTES = 4_000_000
DEFAULT_MAX_TOTAL_PATCH_BYTES = 4_000_000
DEFAULT_MAX_TOTAL_RESULT_BYTES = 4_000_000


class ImplementationError(RuntimeError):
    """Base class for bounded implementation failures."""


class ImplementationLimitError(ImplementationError):
    pass


class DuplicateTargetError(ImplementationError):
    pass


class ImplementationCommitError(ImplementationError):
    def __init__(self, message: str, *, rollback_errors: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.rollback_errors = rollback_errors


@dataclass(frozen=True, slots=True)
class ImplementationRequest:
    patches: tuple[SourcePatch, ...]


class SafeImplementationEngine:
    """Apply a bounded set of prepared text patches as one logical operation."""

    def __init__(
        self,
        patch_engine: TextPatchEngine | None = None,
        *,
        max_patches: int = DEFAULT_MAX_PATCHES,
        max_total_source_bytes: int = DEFAULT_MAX_TOTAL_SOURCE_BYTES,
        max_total_patch_bytes: int = DEFAULT_MAX_TOTAL_PATCH_BYTES,
        max_total_result_bytes: int = DEFAULT_MAX_TOTAL_RESULT_BYTES,
    ) -> None:
        if min(max_patches, max_total_source_bytes, max_total_patch_bytes, max_total_result_bytes) <= 0:
            raise ValueError("implementation limits must be positive")
        self.patch_engine = patch_engine or TextPatchEngine()
        self.max_patches = max_patches
        self.max_total_source_bytes = max_total_source_bytes
        self.max_total_patch_bytes = max_total_patch_bytes
        self.max_total_result_bytes = max_total_result_bytes

    def apply(self, workspace_root: str | Path, request: ImplementationRequest) -> dict[str, object]:
        patches = request.patches
        if not patches:
            raise ImplementationLimitError("implementation request must contain at least one patch")
        if len(patches) > self.max_patches:
            raise ImplementationLimitError("implementation request exceeds the configured patch-count limit")

        normalized_paths: list[str] = []
        for patch in patches:
            normalized_paths.append(self.patch_engine.normalize_path(patch.path))
        if len(set(normalized_paths)) != len(normalized_paths):
            raise DuplicateTargetError("implementation request contains duplicate target paths")

        # Preparation is intentionally side-effect free: every target, digest,
        # diff, and limit is validated before the first filesystem mutation.
        prepared: list[PreparedPatch] = []
        total_source_bytes = 0
        total_patch_bytes = 0
        total_result_bytes = 0
        for patch in patches:
            candidate = self.patch_engine.prepare(workspace_root, patch)
            total_source_bytes += len(candidate.before)
            total_patch_bytes += len(candidate.patch_bytes)
            total_result_bytes += len(candidate.after)
            if total_source_bytes > self.max_total_source_bytes:
                raise ImplementationLimitError("implementation sources exceed the aggregate byte limit")
            if total_patch_bytes > self.max_total_patch_bytes:
                raise ImplementationLimitError("implementation patches exceed the aggregate byte limit")
            if total_result_bytes > self.max_total_result_bytes:
                raise ImplementationLimitError("implementation result exceeds the aggregate byte limit")
            prepared.append(candidate)

        committed: list[PreparedPatch] = []
        try:
            for candidate in prepared:
                self.patch_engine.commit(workspace_root, candidate)
                committed.append(candidate)
        except (PatchError, OSError, RuntimeError) as exc:
            rollback_errors: list[str] = []
            for candidate in reversed(committed):
                try:
                    self.patch_engine.restore(workspace_root, candidate)
                except Exception as rollback_exc:  # rollback failure must remain observable and non-success.
                    rollback_errors.append(f"{candidate.path}: {type(rollback_exc).__name__}: {rollback_exc}")
            message = f"implementation commit failed: {type(exc).__name__}: {exc}"
            if rollback_errors:
                message += "; rollback incomplete"
            raise ImplementationCommitError(message, rollback_errors=tuple(rollback_errors)) from exc

        patch_evidence = [candidate.evidence for candidate in prepared]
        artifacts = [dict(item["artifact"]) for item in patch_evidence]
        workspace_projection = [
            {"path": artifact["path"], "sha256": artifact["sha256"], "size": artifact["size"]}
            for artifact in sorted(artifacts, key=lambda item: str(item["path"]))
        ]
        workspace_digest = sha256(
            json.dumps(workspace_projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {
            "applied": True,
            "protected_stage_authority": False,
            "engine": "safe-source-implementation-v1",
            "workspace_digest": workspace_digest,
            "file_count": len(prepared),
            "total_source_bytes": total_source_bytes,
            "total_patch_bytes": total_patch_bytes,
            "total_result_bytes": total_result_bytes,
            "artifacts": artifacts,
            "patches": patch_evidence,
            "external_execution": False,
            "git_mutation": False,
            "deployment_mutation": False,
        }
