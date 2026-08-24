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

from parallax_api.code.autonomy import AutonomyStopReason
from parallax_api.code.lineage_persistence import (
    PostgresLineageMetadataStore,
    VercelPrivateBlobObjectStore,
)
from parallax_api.code.production_delivery import production_source_delivery
from parallax_api.code.runtime_composition import EngineeringRuntimeComposition
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import SourceLineageStore
from parallax_api.models import EngineeringRun
from parallax_api.projects.model import Project
from parallax_api.db import make_engine


_OWNER_SUBJECT = "canary:production-projected-bootstrap"
_PROJECT_SLUG = "production-projected-bootstrap-canary"


class _CanaryService:
    """Narrow service seam required before the coordinator may mutate PLAN.

    The production runtime bootstrap failure occurs before autonomous stage
    mutation. The canary therefore exposes only owner-independent run lookup and
    intentionally supplies an executor probe that fails closed immediately after
    bootstrap. No PLAN completion, IMPLEMENT mutation, provider publication, or
    Preview delivery can occur through this service.
    """

    event_sink = None

    def __init__(self, run: EngineeringRun) -> None:
        self._run = run

    def get(self, run_id: str) -> EngineeringRun:
        if run_id != self._run.id:
            raise RuntimeError("production runtime canary run identity mismatch")
        return self._run


class _ProbeStopExecutor:
    """Stop autonomy immediately after the protected bootstrap boundary."""

    def probe(self, *, operation_key: str) -> dict[str, object]:
        if not operation_key:
            raise RuntimeError("production runtime canary operation key is required")
        return {
            "protected_success": False,
            "tool_id": "production-runtime-bootstrap-canary",
        }

    def execute(self, spec: object) -> dict[str, object]:
        raise RuntimeError("production runtime canary must never execute a stage command")

    def execute_on_lineage(
        self,
        spec: object,
        *,
        project_ref: str,
        run_id: str,
        source_lineage_ref: str,
    ) -> dict[str, object]:
        raise RuntimeError("production runtime canary must never execute accepted lineage")


def _runtime_for(
    run: EngineeringRun,
    allocator: ProjectWorkspaceAllocator,
    composition: object,
) -> EngineeringRuntimeComposition:
    executor = _ProbeStopExecutor()
    return EngineeringRuntimeComposition(
        _CanaryService(run),  # type: ignore[arg-type]
        allocator,
        executor,
        lineage_executor=executor,
        source_delivery=composition,  # type: ignore[arg-type]
    )


def _run_exact_projected_bootstrap() -> tuple[int, int, str]:
    target = _targets()[0]
    identity = _canary_identity(target.repository_ref)
    engine = make_engine(environment="production")
    lineage_id: str | None = None
    file_count = 0
    total_bytes = 0
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
                    lineage_store = SourceLineageStore(
                        VercelPrivateBlobObjectStore(),
                        metadata,
                    )
                    allocator = ProjectWorkspaceAllocator(root, lineage_store=lineage_store)
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

                    first_runtime = _runtime_for(run, allocator, composition)
                    first_result = first_runtime.run(
                        run_id=identity.run_id,
                        operation_key="preflight:runtime-bootstrap:first",
                        expected_revision=run.revision,
                    )
                    if first_result.stop_reason is not AutonomyStopReason.EXECUTOR_UNAVAILABLE:
                        raise RuntimeError("runtime canary crossed the intended executor-probe stop boundary")
                    if first_result.run is not run or run.state != "PLAN" or run.revision != 1:
                        raise RuntimeError("runtime canary mutated the synthetic Engineering Run")
                    if len(first_result.steps) != 1 or first_result.steps[0].stage != "EXECUTOR":
                        raise RuntimeError("runtime canary produced unexpected autonomous steps")

                    lineage = allocator.current_lineage(identity)
                    lineage_id = lineage.lineage_id
                    file_count = lineage.file_count
                    total_bytes = lineage.total_bytes
                    if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
                        raise RuntimeError("runtime bootstrap lineage identity mismatch")
                    if lineage.parent_lineage_id is not None or lineage.source_kind != "repository":
                        raise RuntimeError("runtime bootstrap violated root-lineage semantics")
                    if lineage.source_ref_digest is None or file_count < 1 or total_bytes < 1:
                        raise RuntimeError("runtime bootstrap returned incomplete source evidence")

                    recreated_runtime = _runtime_for(run, allocator, composition)
                    replay_result = recreated_runtime.run(
                        run_id=identity.run_id,
                        operation_key="preflight:runtime-bootstrap:recreated",
                        expected_revision=run.revision,
                    )
                    if replay_result.stop_reason is not AutonomyStopReason.EXECUTOR_UNAVAILABLE:
                        raise RuntimeError("recreated runtime crossed the intended executor-probe stop boundary")
                    replay_lineage = allocator.current_lineage(identity)
                    if replay_lineage.lineage_id != lineage.lineage_id:
                        raise RuntimeError("recreated runtime bootstrap was not idempotent")
                    if run.state != "PLAN" or run.revision != 1:
                        raise RuntimeError("recreated runtime canary mutated the synthetic Engineering Run")
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
        return file_count, total_bytes, lineage_id
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
    stage = "engineering-runtime-bootstrap"
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
        "engineering_runtime_verified; process_recreation_verified; replay_verified; "
        "no_stage_mutation_verified; metadata_rollback_verified; project_rollback_verified)"
    )


if __name__ == "__main__":
    main()
