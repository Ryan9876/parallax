from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
from time import monotonic

_SCRIPT_ROOT = Path(__file__).resolve().parent
_API_ROOT = _SCRIPT_ROOT.parent
for _path in (_SCRIPT_ROOT, _API_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from production_lineage_composition_preflight import _canary_identity, _targets
from sqlalchemy.orm import sessionmaker

from parallax_api.code.lineage_persistence import PostgresLineageMetadataStore
from parallax_api.code.production_delivery import production_source_delivery
from parallax_api.code.runtime_composition import production_durable_lineage_allocator
from parallax_api.models import EngineeringRun
from parallax_api.projects.model import Project
from parallax_api.db import make_engine


_OWNER_SUBJECT = "canary:production-projected-bootstrap"
_PROJECT_SLUG = "production-projected-bootstrap-canary"


def _run_exact_projected_bootstrap() -> tuple[int, int, str]:
    target = _targets()[0]
    identity = _canary_identity(target.repository_ref)
    engine = make_engine(environment="production")
    lineage_id: str | None = None
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            sessions = sessionmaker(
                bind=connection,
                autoflush=False,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            session = sessions()
            try:
                if session.get(Project, identity.project_id) is not None:
                    raise RuntimeError("synthetic projected-bootstrap Project identity is contaminated")
                metadata = PostgresLineageMetadataStore(sessions)
                if metadata.get_current(identity.project_id, identity.run_id) is not None:
                    raise RuntimeError("synthetic projected-bootstrap lineage identity is contaminated")

                project = Project(
                    id=identity.project_id,
                    owner_subject=_OWNER_SUBJECT,
                    slug=_PROJECT_SLUG,
                    name="Production projected bootstrap canary",
                    description=None,
                    repository_ref=target.repository_ref,
                    workspace_ref=f"project:{identity.project_id}",
                    status="active",
                )
                session.add(project)
                session.flush()

                with tempfile.TemporaryDirectory(prefix="parallax-projected-bootstrap-") as root:
                    allocator = production_durable_lineage_allocator(
                        connection,
                        materialization_root=root,
                    )
                    if allocator is None:
                        raise RuntimeError("production durable lineage allocator is unavailable")
                    composition = production_source_delivery(
                        session,
                        owner_subject=_OWNER_SUBJECT,
                        allocator=allocator,
                        project_id=identity.project_id,
                    )
                    run = EngineeringRun(
                        id=identity.run_id,
                        conversation_id=identity.run_id,
                        spec_id="P2-V0.16.5",
                        project_id=identity.project_id,
                        state="PLAN",
                        revision=1,
                    )

                    first = composition.bootstrap.ensure(
                        run,
                        operation_key="preflight:projected-bootstrap:first",
                    )
                    lineage = first.lineage
                    lineage_id = lineage.lineage_id
                    if not first.initialized:
                        raise RuntimeError("first synthetic projected bootstrap did not initialize lineage")
                    if first.identity != identity:
                        raise RuntimeError("projected bootstrap returned a different Project/run identity")
                    if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
                        raise RuntimeError("projected bootstrap lineage identity mismatch")
                    if lineage.parent_lineage_id is not None or lineage.source_kind != "repository":
                        raise RuntimeError("projected bootstrap violated root-lineage semantics")
                    if lineage.source_ref_digest is None or lineage.file_count < 1 or lineage.total_bytes < 1:
                        raise RuntimeError("projected bootstrap returned incomplete source evidence")

                    replay = composition.bootstrap.ensure(
                        run,
                        operation_key="preflight:projected-bootstrap:replay",
                    )
                    if replay.initialized or replay.lineage.lineage_id != lineage.lineage_id:
                        raise RuntimeError("projected bootstrap replay was not idempotent")
                    durable_current = allocator.current_lineage(identity)
                    if durable_current.lineage_id != lineage.lineage_id:
                        raise RuntimeError("projected bootstrap durable head mismatch")
            finally:
                session.close()
                outer.rollback()

        verification_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        verification_session = verification_sessions()
        try:
            if verification_session.get(Project, identity.project_id) is not None:
                raise RuntimeError("projected bootstrap rollback left a synthetic Project")
        finally:
            verification_session.close()
        verification = PostgresLineageMetadataStore(verification_sessions)
        if verification.get_current(identity.project_id, identity.run_id) is not None:
            raise RuntimeError("projected bootstrap rollback left a synthetic durable head")
        if lineage_id is not None and verification.get_manifest(lineage_id) is not None:
            raise RuntimeError("projected bootstrap rollback left a synthetic durable manifest")
        if lineage_id is None:
            raise RuntimeError("projected bootstrap did not produce a lineage identity")
        return lineage.file_count, lineage.total_bytes, lineage_id
    finally:
        engine.dispose()


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production projected bootstrap preflight: SKIP "
            f"(VERCEL_ENV={environment}; production provider/storage authority remains production-only)"
        )
        return

    started = monotonic()
    stage = "projected-runtime-bootstrap"
    try:
        file_count, total_bytes, _lineage_id = _run_exact_projected_bootstrap()
    except Exception as exc:
        print(
            "Production projected bootstrap preflight: FAIL "
            f"(stage={stage}; error={type(exc).__name__})",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    elapsed_ms = int((monotonic() - started) * 1000)
    print(
        "Production projected bootstrap preflight: PASS "
        f"(files={file_count}; bytes={total_bytes}; elapsed_ms={elapsed_ms}; "
        "replay_verified; metadata_rollback_verified; project_rollback_verified)"
    )


if __name__ == "__main__":
    main()
