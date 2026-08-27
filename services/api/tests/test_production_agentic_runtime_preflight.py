from __future__ import annotations

from pathlib import Path
import sys

import pytest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import production_agentic_runtime_preflight as preflight
from parallax_api.code.agentic_runtime import AgenticRuntimeError
from parallax_api.code.agentic_runtime_live import DurableCandidateArtifactStore
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore


DEPLOYMENT_SHA = "0123456789012345678901234567890123456789"


def test_canary_identity_is_stable_and_release_scoped() -> None:
    first = preflight._canary(DEPLOYMENT_SHA)
    replay = preflight._canary(DEPLOYMENT_SHA)
    other = preflight._canary("1" * 40)

    assert first == replay
    assert first != other
    assert first.project_id != first.run_id
    assert first.base_source_lineage_ref.startswith("src:")
    assert len(first.base_source_lineage_ref) == 68
    assert len(first.plan_id) == 64


def test_candidate_artifact_preflight_round_trips_without_canonical_authority() -> None:
    objects = InMemoryImmutableObjectStore()
    store = DurableCandidateArtifactStore(objects)

    digest = preflight.exercise_candidate_artifact_store(store, DEPLOYMENT_SHA)
    assert len(digest) == 64
    assert digest in objects.objects


def test_candidate_artifact_preflight_rejects_corrupt_immutable_read() -> None:
    objects = InMemoryImmutableObjectStore()
    store = DurableCandidateArtifactStore(objects)
    digest = preflight.exercise_candidate_artifact_store(store, DEPLOYMENT_SHA)
    objects.objects[digest] = b"corrupt"

    canary = preflight._canary(DEPLOYMENT_SHA)
    # The immutable object-store layer verifies the content address first and
    # normalizes a corrupt object as unavailable before the candidate envelope
    # parser can run. Either way the candidate cannot be replayed or mutated.
    with pytest.raises(AgenticRuntimeError, match="artifact is unavailable"):
        store.restore(
            digest,
            request=preflight._request(canary),
            project_ref=canary.project_id,
            run_id=canary.run_id,
            plan_id=canary.plan_id,
            base_source_lineage_ref=canary.base_source_lineage_ref,
            base_revision=canary.base_revision,
        )


def test_production_preflight_requires_exact_activation_flag(monkeypatch, capsys) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", DEPLOYMENT_SHA)
    monkeypatch.delenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", raising=False)

    with pytest.raises(SystemExit) as exc:
        preflight.main()
    assert exc.value.code == 1
    assert "activation flag is not exact 1" in capsys.readouterr().err


def test_nonproduction_preflight_skips_without_blob_mutation(monkeypatch, capsys) -> None:
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.delenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", raising=False)

    preflight.main()
    assert "SKIP" in capsys.readouterr().out
