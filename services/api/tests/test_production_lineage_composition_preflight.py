from __future__ import annotations

from pathlib import Path
import sys
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import production_lineage_composition_preflight as preflight
from parallax_api.code.lineage_persistence import (
    InMemoryImmutableObjectStore,
    PostgresLineageMetadataStore,
    create_lineage_metadata_schema,
)
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage


def test_canary_identity_is_stable_canonical_and_repository_scoped() -> None:
    first = preflight._canary_identity("github:Ryan9876/parallax")
    replay = preflight._canary_identity("github:Ryan9876/parallax")
    other = preflight._canary_identity("github:Ryan9876/other")

    assert first == replay
    assert first != other
    assert str(UUID(first.project_id)) == first.project_id
    assert str(UUID(first.run_id)) == first.run_id
    assert first.project_id != first.run_id


def test_fixed_source_provider_rejects_cross_identity_load() -> None:
    identity = preflight._canary_identity("github:Ryan9876/parallax")
    package = SourcePackage(
        source_kind="repository",
        source_ref="github:Ryan9876/parallax@0123456789012345678901234567890123456789",
        files={"README.md": b"Parallax\n"},
    )
    provider = preflight._FixedSourceProvider(identity, package)

    assert provider.load(identity) is package

    other = ProjectRunIdentity(project_id=str(uuid4()), run_id=str(uuid4()))
    try:
        provider.load(other)
    except RuntimeError as exc:
        assert "identity mismatch" in str(exc)
    else:  # pragma: no cover - assertion helper
        raise AssertionError("cross-identity canary source load must fail closed")


def test_lineage_composition_source_policy_excludes_secret_paths() -> None:
    assert preflight._lineage_secret_sensitive("services/api/.env.production") is True
    assert preflight._lineage_secret_sensitive("keys/service.pem") is True
    assert preflight._lineage_secret_sensitive("src/main.py") is False

    assert preflight._provider_path_valid("services/api/parallax_api/main.py") is True
    assert preflight._provider_path_valid("../escape.py") is False
    assert preflight._provider_path_valid("credentials/token.txt") is False


def test_outer_transaction_rolls_back_synthetic_lineage_metadata(tmp_path) -> None:
    # Python's sqlite3 defaults to legacy transaction control through 3.15,
    # where released SAVEPOINTs can escape an outer rollback. Enable modern
    # transaction control so this test exercises the same external-transaction
    # invariant the production PostgreSQL canary relies on.
    engine = create_engine(
        f"sqlite:///{tmp_path / 'lineage-canary.db'}",
        future=True,
        connect_args={"check_same_thread": False, "autocommit": False},
    )
    create_lineage_metadata_schema(engine)
    identity = preflight._canary_identity("github:Ryan9876/parallax")
    package = SourcePackage(
        source_kind="repository",
        source_ref="github:Ryan9876/parallax@0123456789012345678901234567890123456789",
        files={"README.md": b"Parallax\n", "src/app.py": b"value = 1\n"},
    )
    lineage_id: str | None = None

    with engine.connect() as connection:
        outer = connection.begin()
        sessions = sessionmaker(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        metadata = PostgresLineageMetadataStore(sessions)
        store = SourceLineageStore(InMemoryImmutableObjectStore(), metadata)
        allocator = ProjectWorkspaceAllocator(tmp_path / "workspaces", lineage_store=store)
        workspace = allocator.initialize(identity, preflight._FixedSourceProvider(identity, package))
        lineage_id = workspace.lineage.lineage_id
        assert metadata.get_current(identity.project_id, identity.run_id) == lineage_id
        assert metadata.get_manifest(lineage_id) is not None
        allocator.cleanup(workspace)
        outer.rollback()

    verification = PostgresLineageMetadataStore(
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    )
    assert verification.get_current(identity.project_id, identity.run_id) is None
    assert lineage_id is not None
    assert verification.get_manifest(lineage_id) is None
    engine.dispose()
