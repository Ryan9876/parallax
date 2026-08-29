from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal
from ..code.runtime_composition import production_durable_lineage_allocator
from ..code.source_delivery_composition import EngineeringAttemptDeliveryRecordStore
from ..code.source_only_delivery import SourceOnlyDeliveryResult
from ..code.workspace_lineage import ProjectRunIdentity
from ..db import get_session
from ..projects.repository import ProjectRepository
from ..repositories.engineering_runs import EngineeringRunRepository


router = APIRouter(prefix="/v1/projects", tags=["source-handoff"])
_MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024


@router.get("/{project_id}/engineering-runs/{run_id}/source-download")
def download_source_handoff(
    project_id: str,
    run_id: str,
    principal: AccessPrincipal = Depends(access_principal),
    session: Session = Depends(get_session),
):
    projects = ProjectRepository(session)
    project = projects.get_for_owner(project_id, principal.subject)
    if project is None or project.status != "active":
        raise HTTPException(404, "Project not found")
    if project.delivery_mode != "source-only":
        raise HTTPException(409, "Project is not configured for source-only handoff")

    runs = EngineeringRunRepository(session)
    run = runs.get(run_id)
    if run is None or run.project_id != project.id:
        raise HTTPException(404, "Engineering Run not found")
    if run.state != "REVIEW":
        raise HTTPException(409, "Accepted source can be downloaded only at REVIEW")

    allocator = production_durable_lineage_allocator(session.get_bind())
    if allocator is None:
        raise HTTPException(503, "Durable source lineage is unavailable")
    identity = ProjectRunIdentity(project_id=project.id, run_id=run.id)
    try:
        current = allocator.current_lineage(identity)
    except Exception as exc:
        raise HTTPException(503, "Accepted source lineage is unavailable") from exc

    payload = EngineeringAttemptDeliveryRecordStore(runs).load(
        run_id=run.id,
        lineage_id=current.lineage_id,
    )
    if payload is None:
        raise HTTPException(409, "Source-only handoff has not been recorded")
    try:
        handoff = SourceOnlyDeliveryResult.from_record(payload, replayed=True)
    except Exception as exc:
        raise HTTPException(503, "Source-only handoff evidence is invalid") from exc
    if (
        handoff.project_id != project.id
        or handoff.run_id != run.id
        or handoff.lineage_id != current.lineage_id
        or handoff.content_digest != current.content_digest
    ):
        raise HTTPException(503, "Source-only handoff evidence does not match accepted lineage")

    workspace = None
    try:
        workspace = allocator.reconstruct(identity, current.lineage_id)
        lineage = workspace.lineage
        if (
            workspace.identity != identity
            or lineage.project_id != project.id
            or lineage.run_id != run.id
            or lineage.lineage_id != current.lineage_id
            or lineage.content_digest != current.content_digest
        ):
            raise HTTPException(503, "Reconstructed source does not match accepted lineage")

        root = workspace.path.resolve(strict=True)
        total = 0
        archive = BytesIO()
        with ZipFile(archive, mode="w", compression=ZIP_DEFLATED) as bundle:
            for entry in sorted(lineage.files, key=lambda item: item.path):
                pure = PurePosixPath(entry.path)
                if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                    raise HTTPException(503, "Accepted source contains an unsafe path")
                target = workspace.path.joinpath(*pure.parts)
                if target.is_symlink() or not target.is_file():
                    raise HTTPException(503, "Accepted source file is unavailable")
                resolved = target.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise HTTPException(503, "Accepted source escaped the protected workspace")
                raw = target.read_bytes()
                if len(raw) != entry.size or sha256(raw).hexdigest() != entry.sha256:
                    raise HTTPException(503, "Accepted source file failed lineage verification")
                total += len(raw)
                if total > _MAX_DOWNLOAD_BYTES:
                    raise HTTPException(413, "Accepted source exceeds the bounded download size")
                bundle.writestr(entry.path, raw)
        body = archive.getvalue()
    finally:
        if workspace is not None:
            try:
                allocator.cleanup(workspace)
            except Exception:
                pass

    safe_slug = project.slug[:60]
    filename = f"parallax-{safe_slug}-{run.id[:8]}.zip"
    return Response(
        content=body,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Parallax-Handoff-ID": handoff.handoff_id,
            "Cache-Control": "private, no-store",
        },
    )
