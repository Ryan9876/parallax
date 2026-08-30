from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .lineage_persistence import DurableLineagePersistenceError, MetadataCASConflict
from .workspace_lineage import (
    HEX_SHA256,
    LINEAGE_VERSION,
    LineageIntegrityError,
    ProjectRunIdentity,
    SourceLineage,
    SourceLineageStore,
    SourcePolicyError,
    StaleLineageError,
)


GREENFIELD_SOURCE_KIND = "greenfield"
GREENFIELD_SOURCE_REF_VERSION = "v1"
EMPTY_CONTENT_DIGEST = SourceLineageStore._content_digest(())


def greenfield_source_ref(repository_ref: str, default_branch: str) -> str:
    """Return bounded provenance text for a positively inspected empty repository."""

    if not isinstance(repository_ref, str) or not repository_ref.startswith("github:"):
        raise SourcePolicyError("greenfield repository identity must be canonical GitHub repository text")
    repository = repository_ref.removeprefix("github:")
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise SourcePolicyError("greenfield repository identity is invalid")
    if not isinstance(default_branch, str) or not default_branch or len(default_branch.encode("utf-8")) > 160:
        raise SourcePolicyError("greenfield default branch is invalid")
    if any(character in default_branch for character in ("\x00", "\n", "\r", "@", ":")):
        raise SourcePolicyError("greenfield default branch is invalid")
    return f"{repository_ref}@greenfield-empty:{default_branch}:{GREENFIELD_SOURCE_REF_VERSION}"


class GreenfieldSourceLineageStore(SourceLineageStore):
    """Narrow zero-file root extension for positively proven empty repositories.

    Ordinary SourcePackage initialization remains unchanged and therefore
    non-empty. Only initialize_greenfield can create an empty root. Accepted
    implementation capture still uses the base store and requires at least one
    regular protected source file.
    """

    def initialize_greenfield(
        self,
        identity: ProjectRunIdentity,
        *,
        source_ref: str,
    ) -> SourceLineage:
        source_ref_digest = self._source_ref_digest(source_ref)
        prepared = self._prepare_contents({})
        if prepared.content_digest != EMPTY_CONTENT_DIGEST or prepared.files or prepared.total_bytes != 0:
            raise LineageIntegrityError("canonical greenfield empty tree is invalid")
        candidate = self._lineage(
            identity,
            prepared,
            parent_lineage_id=None,
            source_kind=GREENFIELD_SOURCE_KIND,
            source_ref_digest=source_ref_digest,
        )
        self._persist_prepared(prepared)
        try:
            result = self.metadata_store.commit_manifest_and_advance(
                project_id=identity.project_id,
                run_id=identity.run_id,
                lineage_id=candidate.lineage_id,
                manifest=self._serialized_manifest(candidate),
                expected_current_lineage_id=None,
            )
        except MetadataCASConflict as exc:
            if exc.current_lineage_id == candidate.lineage_id:
                return self.resolve(identity, candidate.lineage_id)
            raise StaleLineageError("source lineage is already initialized for this Project/run") from exc
        except DurableLineagePersistenceError as exc:
            raise LineageIntegrityError("durable greenfield metadata could not be committed") from exc
        if result.lineage_id != candidate.lineage_id:
            raise LineageIntegrityError("durable metadata returned a different greenfield lineage")
        return self.resolve(identity, candidate.lineage_id)

    def materialize(
        self,
        identity: ProjectRunIdentity,
        lineage_id: str,
        target_root: str | Path,
    ) -> SourceLineage:
        lineage = self.resolve(identity, lineage_id)
        if lineage.source_kind != GREENFIELD_SOURCE_KIND:
            return super().materialize(identity, lineage_id, target_root)
        self._require_greenfield_root(lineage)
        target = Path(target_root)
        if target.exists() or target.is_symlink():
            raise SourcePolicyError("materialization target must not already exist")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()
        return lineage

    def _lineage_from_manifest(self, payload: object) -> SourceLineage:
        if not isinstance(payload, dict) or payload.get("source_kind") != GREENFIELD_SOURCE_KIND:
            return super()._lineage_from_manifest(payload)
        if payload.get("version") != LINEAGE_VERSION:
            raise LineageIntegrityError("source lineage manifest version is invalid")
        try:
            identity = ProjectRunIdentity(str(payload["project_id"]), str(payload["run_id"]))
            lineage_id = str(payload["lineage_id"])
            self._validate_lineage_id(lineage_id)
            parent = payload.get("parent_lineage_id")
            content_digest = str(payload["content_digest"])
            source_ref_digest = payload.get("source_ref_digest")
            raw_files = payload["files"]
            file_count = payload.get("file_count")
            total_bytes = payload.get("total_bytes")
        except (KeyError, TypeError, ValueError) as exc:
            raise LineageIntegrityError("greenfield source lineage manifest shape is invalid") from exc
        if parent is not None:
            raise LineageIntegrityError("greenfield root cannot have a parent lineage")
        if content_digest != EMPTY_CONTENT_DIGEST:
            raise LineageIntegrityError("greenfield root content digest is not canonical empty state")
        if not isinstance(source_ref_digest, str) or not HEX_SHA256.fullmatch(source_ref_digest):
            raise LineageIntegrityError("greenfield source provenance digest is invalid")
        if raw_files != [] or file_count != 0 or total_bytes != 0:
            raise LineageIntegrityError("greenfield root must contain exactly zero source files")
        lineage = SourceLineage(
            project_id=identity.project_id,
            run_id=identity.run_id,
            lineage_id=lineage_id,
            parent_lineage_id=None,
            content_digest=content_digest,
            source_kind=GREENFIELD_SOURCE_KIND,
            source_ref_digest=source_ref_digest,
            file_count=0,
            total_bytes=0,
            files=(),
        )
        self._require_greenfield_root(lineage)
        return lineage

    @staticmethod
    def _require_greenfield_root(lineage: SourceLineage) -> None:
        if (
            lineage.source_kind != GREENFIELD_SOURCE_KIND
            or lineage.parent_lineage_id is not None
            or lineage.content_digest != EMPTY_CONTENT_DIGEST
            or lineage.source_ref_digest is None
            or not HEX_SHA256.fullmatch(lineage.source_ref_digest)
            or lineage.file_count != 0
            or lineage.total_bytes != 0
            or lineage.files != ()
        ):
            raise LineageIntegrityError("greenfield root lineage invariants are invalid")


__all__ = [
    "EMPTY_CONTENT_DIGEST",
    "GREENFIELD_SOURCE_KIND",
    "GREENFIELD_SOURCE_REF_VERSION",
    "GreenfieldSourceLineageStore",
    "greenfield_source_ref",
]
