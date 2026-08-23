from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from threading import RLock
from typing import Callable, Protocol

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    and_,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class DurableLineagePersistenceError(RuntimeError):
    pass


class ObjectStoreError(DurableLineagePersistenceError):
    pass


class ObjectMissingError(ObjectStoreError, LookupError):
    pass


class ObjectIntegrityError(ObjectStoreError):
    pass


class ObjectWriteError(ObjectStoreError):
    pass


class MetadataStoreError(DurableLineagePersistenceError):
    pass


class MetadataIntegrityError(MetadataStoreError):
    pass


class MetadataCASConflict(MetadataStoreError):
    def __init__(self, current_lineage_id: str | None) -> None:
        super().__init__("durable current-lineage compare-and-swap failed")
        self.current_lineage_id = current_lineage_id


class ImmutableObjectStore(Protocol):
    def put_if_absent(self, digest: str, content: bytes) -> None: ...

    def get(self, digest: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class MetadataCommitResult:
    lineage_id: str
    replayed: bool


class LineageMetadataStore(Protocol):
    def get_current(self, project_id: str, run_id: str) -> str | None: ...

    def get_manifest(self, lineage_id: str) -> bytes | None: ...

    def commit_manifest_and_advance(
        self,
        *,
        project_id: str,
        run_id: str,
        lineage_id: str,
        manifest: bytes,
        expected_current_lineage_id: str | None,
    ) -> MetadataCommitResult: ...


class InMemoryImmutableObjectStore:
    """Deterministic durable-object fake for tests and local development.

    State belongs to this adapter instance rather than a materialization path, so
    multiple SourceLineageStore instances can exercise process-recreation and CAS
    behavior without making a local workspace authoritative.
    """

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self._lock = RLock()

    def put_if_absent(self, digest: str, content: bytes) -> None:
        _validate_digest(digest)
        payload = bytes(content)
        if sha256(payload).hexdigest() != digest:
            raise ObjectIntegrityError("object content does not match its content address")
        with self._lock:
            existing = self.objects.get(digest)
            if existing is not None:
                if sha256(existing).hexdigest() != digest or existing != payload:
                    raise ObjectIntegrityError("existing immutable object differs from its content address")
                return
            self.objects[digest] = payload

    def get(self, digest: str) -> bytes:
        _validate_digest(digest)
        with self._lock:
            content = self.objects.get(digest)
        if content is None:
            raise ObjectMissingError("durable source object is missing")
        payload = bytes(content)
        if sha256(payload).hexdigest() != digest:
            raise ObjectIntegrityError("durable source object digest mismatch")
        return payload


class InMemoryLineageMetadataStore:
    """Transactional metadata/CAS fake shared across simulated API instances."""

    def __init__(self) -> None:
        self.manifests: dict[str, bytes] = {}
        self.heads: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def get_current(self, project_id: str, run_id: str) -> str | None:
        with self._lock:
            return self.heads.get((project_id, run_id))

    def get_manifest(self, lineage_id: str) -> bytes | None:
        with self._lock:
            manifest = self.manifests.get(lineage_id)
        return None if manifest is None else bytes(manifest)

    def commit_manifest_and_advance(
        self,
        *,
        project_id: str,
        run_id: str,
        lineage_id: str,
        manifest: bytes,
        expected_current_lineage_id: str | None,
    ) -> MetadataCommitResult:
        payload = bytes(manifest)
        key = (project_id, run_id)
        with self._lock:
            existing_manifest = self.manifests.get(lineage_id)
            if existing_manifest is not None and existing_manifest != payload:
                raise MetadataIntegrityError("immutable lineage manifest changed for an existing lineage id")

            current = self.heads.get(key)
            if current == lineage_id:
                if existing_manifest is None:
                    raise MetadataIntegrityError("durable head references a missing lineage manifest")
                return MetadataCommitResult(lineage_id=lineage_id, replayed=True)
            if current != expected_current_lineage_id:
                raise MetadataCASConflict(current)

            self.manifests.setdefault(lineage_id, payload)
            self.heads[key] = lineage_id
            return MetadataCommitResult(lineage_id=lineage_id, replayed=False)


class VercelPrivateBlobObjectStore:
    """Private Vercel Blob adapter for immutable SHA-256 addressed source bytes.

    Only server-derived digest paths are accepted. Tokens are passed only to the
    provider SDK and are never returned as lineage/evaluation evidence.
    """

    def __init__(
        self,
        *,
        prefix: str = "parallax/source-lineage/v1/sha256",
        token: str | None = None,
    ) -> None:
        normalized = prefix.strip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValueError("durable object prefix must be a protected relative prefix")
        self.prefix = normalized
        self.token = token

    def put_if_absent(self, digest: str, content: bytes) -> None:
        _validate_digest(digest)
        payload = bytes(content)
        if sha256(payload).hexdigest() != digest:
            raise ObjectIntegrityError("object content does not match its content address")
        path = self._path(digest)

        try:
            existing = self._provider_get(path)
        except ObjectMissingError:
            existing = None
        if existing is not None:
            if existing != payload:
                raise ObjectIntegrityError("existing private object differs from its content address")
            return

        try:
            from vercel.blob import BlobError, put

            put(
                path,
                payload,
                access="private",
                content_type="application/octet-stream",
                add_random_suffix=False,
                overwrite=False,
                token=self.token,
            )
        except BlobError as exc:
            # A concurrent writer may have won the immutable pathname race.
            # Re-read and accept only the exact content-addressed object.
            try:
                raced = self._provider_get(path)
            except ObjectStoreError:
                raise ObjectWriteError("private durable object write failed") from exc
            if raced != payload:
                raise ObjectWriteError("private durable object write conflicted with different content") from exc

        verified = self._provider_get(path)
        if verified != payload:
            raise ObjectIntegrityError("private durable object failed write-after-read verification")

    def get(self, digest: str) -> bytes:
        _validate_digest(digest)
        return self._provider_get(self._path(digest), expected_digest=digest)

    def _provider_get(self, path: str, *, expected_digest: str | None = None) -> bytes:
        try:
            from vercel.blob import BlobError, BlobNotFoundError, get

            result = get(path, access="private", token=self.token, use_cache=False)
        except BlobNotFoundError as exc:
            raise ObjectMissingError("private durable source object is missing") from exc
        except BlobError as exc:
            raise ObjectStoreError("private durable source object read failed") from exc
        payload = bytes(result.content)
        digest = expected_digest or path.rsplit("/", 1)[-1]
        _validate_digest(digest)
        if sha256(payload).hexdigest() != digest:
            raise ObjectIntegrityError("private durable source object digest mismatch")
        return payload

    def _path(self, digest: str) -> str:
        return f"{self.prefix}/{digest[:2]}/{digest}"


LINEAGE_METADATA = MetaData()

SOURCE_LINEAGE_MANIFESTS = Table(
    "source_lineage_manifests",
    LINEAGE_METADATA,
    Column("lineage_id", String(68), primary_key=True),
    Column("project_id", String(36), nullable=False, index=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("parent_lineage_id", String(68), nullable=True),
    Column("manifest_sha256", String(64), nullable=False),
    Column("manifest_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

SOURCE_LINEAGE_HEADS = Table(
    "source_lineage_heads",
    LINEAGE_METADATA,
    Column("project_id", String(36), primary_key=True),
    Column("run_id", String(36), primary_key=True),
    Column("lineage_id", String(68), nullable=False),
    Column("revision", BigInteger, nullable=False, default=0),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def create_lineage_metadata_schema(engine: Engine) -> None:
    """Create only the lineage metadata tables for isolated adapter tests.

    Production uses the committed forward migration; runtime code never calls
    this helper automatically.
    """

    LINEAGE_METADATA.create_all(engine)


class PostgresLineageMetadataStore:
    """Transactional persistent metadata with expected-current CAS advancement.

    The adapter uses SQLAlchemy sessions so production runs through Parallax's
    existing Postgres/Supavisor boundary. The conditional UPDATE is the durable
    concurrency arbiter; no process-local lock is required for correctness.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def get_current(self, project_id: str, run_id: str) -> str | None:
        with self.session_factory() as session:
            return session.execute(
                select(SOURCE_LINEAGE_HEADS.c.lineage_id).where(
                    SOURCE_LINEAGE_HEADS.c.project_id == project_id,
                    SOURCE_LINEAGE_HEADS.c.run_id == run_id,
                )
            ).scalar_one_or_none()

    def get_manifest(self, lineage_id: str) -> bytes | None:
        with self.session_factory() as session:
            row = session.execute(
                select(
                    SOURCE_LINEAGE_MANIFESTS.c.manifest_json,
                    SOURCE_LINEAGE_MANIFESTS.c.manifest_sha256,
                ).where(SOURCE_LINEAGE_MANIFESTS.c.lineage_id == lineage_id)
            ).one_or_none()
        if row is None:
            return None
        payload = row.manifest_json.encode("utf-8")
        if sha256(payload).hexdigest() != row.manifest_sha256:
            raise MetadataIntegrityError("durable lineage manifest checksum mismatch")
        return payload

    def commit_manifest_and_advance(
        self,
        *,
        project_id: str,
        run_id: str,
        lineage_id: str,
        manifest: bytes,
        expected_current_lineage_id: str | None,
    ) -> MetadataCommitResult:
        payload = bytes(manifest)
        payload_text = payload.decode("utf-8")
        manifest_digest = sha256(payload).hexdigest()
        now = datetime.now(timezone.utc)

        with self.session_factory() as session:
            try:
                with session.begin():
                    existing = session.execute(
                        select(
                            SOURCE_LINEAGE_MANIFESTS.c.manifest_json,
                            SOURCE_LINEAGE_MANIFESTS.c.manifest_sha256,
                        ).where(SOURCE_LINEAGE_MANIFESTS.c.lineage_id == lineage_id)
                    ).one_or_none()
                    if existing is not None:
                        existing_payload = existing.manifest_json.encode("utf-8")
                        if (
                            existing.manifest_sha256 != manifest_digest
                            or existing_payload != payload
                            or sha256(existing_payload).hexdigest() != existing.manifest_sha256
                        ):
                            raise MetadataIntegrityError(
                                "immutable durable lineage manifest differs from existing metadata"
                            )
                    else:
                        self._insert_manifest_if_absent(
                            session,
                            project_id=project_id,
                            run_id=run_id,
                            lineage_id=lineage_id,
                            parent_lineage_id=expected_current_lineage_id,
                            manifest_sha256=manifest_digest,
                            manifest_json=payload_text,
                            created_at=now,
                        )
                        persisted = session.execute(
                            select(
                                SOURCE_LINEAGE_MANIFESTS.c.manifest_json,
                                SOURCE_LINEAGE_MANIFESTS.c.manifest_sha256,
                            ).where(SOURCE_LINEAGE_MANIFESTS.c.lineage_id == lineage_id)
                        ).one()
                        if (
                            persisted.manifest_sha256 != manifest_digest
                            or persisted.manifest_json.encode("utf-8") != payload
                        ):
                            raise MetadataIntegrityError(
                                "concurrent durable manifest insert produced different immutable metadata"
                            )

                    current = session.execute(
                        select(SOURCE_LINEAGE_HEADS.c.lineage_id).where(
                            SOURCE_LINEAGE_HEADS.c.project_id == project_id,
                            SOURCE_LINEAGE_HEADS.c.run_id == run_id,
                        )
                    ).scalar_one_or_none()
                    if current == lineage_id:
                        return MetadataCommitResult(lineage_id=lineage_id, replayed=True)
                    if current != expected_current_lineage_id:
                        raise MetadataCASConflict(current)

                    if expected_current_lineage_id is None:
                        self._insert_head_if_absent(
                            session,
                            project_id=project_id,
                            run_id=run_id,
                            lineage_id=lineage_id,
                            updated_at=now,
                        )
                        durable_current = session.execute(
                            select(SOURCE_LINEAGE_HEADS.c.lineage_id).where(
                                SOURCE_LINEAGE_HEADS.c.project_id == project_id,
                                SOURCE_LINEAGE_HEADS.c.run_id == run_id,
                            )
                        ).scalar_one_or_none()
                        if durable_current != lineage_id:
                            raise MetadataCASConflict(durable_current)
                    else:
                        result = session.execute(
                            update(SOURCE_LINEAGE_HEADS)
                            .where(
                                SOURCE_LINEAGE_HEADS.c.project_id == project_id,
                                SOURCE_LINEAGE_HEADS.c.run_id == run_id,
                                SOURCE_LINEAGE_HEADS.c.lineage_id == expected_current_lineage_id,
                            )
                            .values(
                                lineage_id=lineage_id,
                                revision=SOURCE_LINEAGE_HEADS.c.revision + 1,
                                updated_at=now,
                            )
                        )
                        if result.rowcount != 1:
                            durable_current = session.execute(
                                select(SOURCE_LINEAGE_HEADS.c.lineage_id).where(
                                    SOURCE_LINEAGE_HEADS.c.project_id == project_id,
                                    SOURCE_LINEAGE_HEADS.c.run_id == run_id,
                                )
                            ).scalar_one_or_none()
                            if durable_current == lineage_id:
                                return MetadataCommitResult(lineage_id=lineage_id, replayed=True)
                            raise MetadataCASConflict(durable_current)
            except (MetadataCASConflict, MetadataIntegrityError):
                raise
            except Exception as exc:
                raise MetadataStoreError("transactional durable lineage metadata write failed") from exc

        return MetadataCommitResult(lineage_id=lineage_id, replayed=False)

    @staticmethod
    def _insert_manifest_if_absent(session: Session, **values: object) -> None:
        statement = _insert_do_nothing(session, SOURCE_LINEAGE_MANIFESTS, values, ("lineage_id",))
        session.execute(statement)

    @staticmethod
    def _insert_head_if_absent(session: Session, **values: object) -> None:
        statement = _insert_do_nothing(
            session,
            SOURCE_LINEAGE_HEADS,
            values,
            ("project_id", "run_id"),
        )
        session.execute(statement)


def _insert_do_nothing(
    session: Session,
    table: Table,
    values: dict[str, object],
    conflict_columns: tuple[str, ...],
):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        raise MetadataStoreError(f"durable lineage metadata requires PostgreSQL-compatible CAS; unsupported {dialect}")
    return dialect_insert(table).values(**values).on_conflict_do_nothing(
        index_elements=[table.c[name] for name in conflict_columns]
    )


def _validate_digest(digest: str) -> None:
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ObjectIntegrityError("durable object digest must be lowercase SHA-256")


__all__ = [
    "DurableLineagePersistenceError",
    "ImmutableObjectStore",
    "InMemoryImmutableObjectStore",
    "InMemoryLineageMetadataStore",
    "LINEAGE_METADATA",
    "LineageMetadataStore",
    "MetadataCASConflict",
    "MetadataCommitResult",
    "MetadataIntegrityError",
    "MetadataStoreError",
    "ObjectIntegrityError",
    "ObjectMissingError",
    "ObjectStoreError",
    "ObjectWriteError",
    "PostgresLineageMetadataStore",
    "SOURCE_LINEAGE_HEADS",
    "SOURCE_LINEAGE_MANIFESTS",
    "VercelPrivateBlobObjectStore",
    "create_lineage_metadata_schema",
]
