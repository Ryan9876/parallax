from __future__ import annotations

import json
from hashlib import sha256
from types import SimpleNamespace
from zipfile import ZipFile
from io import BytesIO

import pytest
from fastapi import HTTPException

from parallax_api.code.source_only_delivery import SourceOnlyDeliveryResult
from parallax_api.code.workspace_lineage import ProjectRunIdentity
from parallax_api.routes import source_handoff as module


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
LINEAGE_ID = "src:" + "a" * 64
CONTENT_DIGEST = "b" * 64
HANDOFF_ID = "handoff:" + "c" * 64


def _install_repository_fakes(monkeypatch, *, project, run, attempt):
    monkeypatch.setattr(module.ProjectRepository, "get_for_owner", lambda self, project_id, owner: project)
    monkeypatch.setattr(module.EngineeringRunRepository, "get", lambda self, run_id: run)
    monkeypatch.setattr(module.EngineeringRunRepository, "find_operation", lambda self, run_id, operation_key: attempt)


def test_source_download_is_owner_scoped(monkeypatch) -> None:
    monkeypatch.setattr(module.ProjectRepository, "get_for_owner", lambda self, project_id, owner: None)
    with pytest.raises(HTTPException) as caught:
        module.download_source_handoff(
            PROJECT_ID,
            RUN_ID,
            principal=SimpleNamespace(subject="owner:test"),
            session=SimpleNamespace(),
        )
    assert caught.value.status_code == 404


def test_source_download_requires_source_only_review(monkeypatch) -> None:
    project = SimpleNamespace(id=PROJECT_ID, status="active", delivery_mode="vercel-preview", slug="demo")
    monkeypatch.setattr(module.ProjectRepository, "get_for_owner", lambda self, project_id, owner: project)
    with pytest.raises(HTTPException) as caught:
        module.download_source_handoff(
            PROJECT_ID,
            RUN_ID,
            principal=SimpleNamespace(subject="owner:test"),
            session=SimpleNamespace(),
        )
    assert caught.value.status_code == 409


def test_source_download_reconstructs_exact_recorded_lineage(monkeypatch, tmp_path) -> None:
    project = SimpleNamespace(id=PROJECT_ID, status="active", delivery_mode="source-only", slug="demo")
    run = SimpleNamespace(id=RUN_ID, project_id=PROJECT_ID, state="REVIEW")
    raw = b"hello from accepted lineage\n"
    target = tmp_path / "README.md"
    target.write_bytes(raw)
    entry = SimpleNamespace(path="README.md", size=len(raw), sha256=sha256(raw).hexdigest())
    lineage = SimpleNamespace(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        lineage_id=LINEAGE_ID,
        content_digest=CONTENT_DIGEST,
        files=(entry,),
    )
    identity = ProjectRunIdentity(project_id=PROJECT_ID, run_id=RUN_ID)
    workspace = SimpleNamespace(identity=identity, lineage=lineage, path=tmp_path)
    handoff = SourceOnlyDeliveryResult(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        repository_identity_digest="d" * 64,
        lineage_id=LINEAGE_ID,
        content_digest=CONTENT_DIGEST,
        handoff_id=HANDOFF_ID,
    )
    attempt = SimpleNamespace(
        stage="SOURCE_DELIVERY",
        status="RECORDED",
        evidence_json=json.dumps(handoff.to_record(), sort_keys=True, separators=(",", ":")),
    )
    _install_repository_fakes(monkeypatch, project=project, run=run, attempt=attempt)

    class Allocator:
        cleaned = False

        def current_lineage(self, requested_identity):
            assert requested_identity == identity
            return lineage

        def reconstruct(self, requested_identity, lineage_id):
            assert requested_identity == identity
            assert lineage_id == LINEAGE_ID
            return workspace

        def cleanup(self, received):
            assert received is workspace
            self.cleaned = True

    allocator = Allocator()
    monkeypatch.setattr(module, "production_durable_lineage_allocator", lambda engine: allocator)
    session = SimpleNamespace(get_bind=lambda: object())

    response = module.download_source_handoff(
        PROJECT_ID,
        RUN_ID,
        principal=SimpleNamespace(subject="owner:test"),
        session=session,
    )

    assert response.media_type == "application/zip"
    assert response.headers["x-parallax-handoff-id"] == HANDOFF_ID
    assert response.headers["cache-control"] == "private, no-store"
    assert allocator.cleaned is True
    assert b"vercel" not in response.body.lower()
    with ZipFile(BytesIO(response.body), "r") as archive:
        assert archive.namelist() == ["README.md"]
        assert archive.read("README.md") == raw
