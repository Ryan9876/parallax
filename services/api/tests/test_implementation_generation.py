from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from parallax_api.code.source_context import (
    BoundedSourceContextSelector,
    SourceContextSnapshot,
)
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    GeneratedSourcePatch,
    ImplementationGenerationCoordinator,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
from parallax_api.intelligence.router import ModelRouter


def proposal(*, acceptance_ids=None, path="src/app.py", digest=None, replacement="value = 2"):
    digest = digest or sha256(b"value = 1\n").hexdigest()
    return ImplementationProposal(
        acceptance_ids_covered=acceptance_ids or ["AC-01", "AC-02"],
        patches=[
            GeneratedSourcePatch(
                path=path,
                expected_base_sha256=digest,
                unified_diff=(
                    f"--- a/{path}\n"
                    f"+++ b/{path}\n"
                    "@@ -1 +1 @@\n"
                    "-value = 1\n"
                    f"+{replacement}\n"
                ),
            )
        ],
    )


def generation_request(snapshot: SourceContextSnapshot) -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id="ws-1",
        work_specification_revision=1,
        work_specification_digest="a" * 64,
        title="Protected implementation",
        objective="Change the application value safely.",
        constraints=("Do not broaden authority.",),
        acceptance=(
            AcceptanceRequirement("AC-01", "The value changes."),
            AcceptanceRequirement("AC-02", "Protected authority remains bounded."),
        ),
        source_context=snapshot,
    )


def test_proposal_rejects_extra_authority_and_hidden_reasoning_fields():
    base = {
        "acceptance_ids_covered": ["AC-01", "AC-02"],
        "patches": [
            {
                "path": "src/app.py",
                "expected_base_sha256": "a" * 64,
                "unified_diff": "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-a\n+b\n",
            }
        ],
    }
    for forbidden in ("workspace_root", "command", "environment", "chain_of_thought", "scratchpad"):
        with pytest.raises(ValidationError):
            ImplementationProposal.model_validate({**base, forbidden: "not-authority"})


def test_proposal_rejects_duplicate_targets_and_malformed_digest():
    patch = {
        "path": "src/app.py",
        "expected_base_sha256": "a" * 64,
        "unified_diff": "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-a\n+b\n",
    }
    with pytest.raises(ValidationError):
        ImplementationProposal.model_validate(
            {"acceptance_ids_covered": ["AC-01"], "patches": [patch, patch]}
        )
    with pytest.raises(ValidationError):
        GeneratedSourcePatch.model_validate({**patch, "expected_base_sha256": "not-a-digest"})


def test_acceptance_coverage_is_exact_and_ordered():
    required = ("AC-01", "AC-02")
    assert validate_implementation_proposal(proposal(), required)
    assert not validate_implementation_proposal(proposal(acceptance_ids=["AC-02", "AC-01"]), required)
    assert not validate_implementation_proposal(proposal(acceptance_ids=["AC-01"]), required)
    assert not validate_implementation_proposal(proposal(acceptance_ids=["AC-01", "AC-02", "AC-03"]), required)


def test_router_escalates_invalid_candidate_then_accepts_exact_candidate():
    snapshot = SourceContextSnapshot(files=(), digest="0" * 64, total_bytes=0, excluded_secret_files=0, omitted_bounded_files=0)
    request = generation_request(snapshot)
    seen: list[str] = []

    class Program:
        version = "fake-generation-v1"

        def __init__(self, model: str):
            self.model = model

        def run(self, *, request):
            seen.append(self.model)
            if self.model == "luna":
                return proposal(acceptance_ids=["AC-02", "AC-01"])
            return proposal()

    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(models=("luna", "terra", "sol")),
        program_factory=Program,
    )
    result = coordinator.generate_sync(request)
    assert result.model == "terra"
    assert seen == ["luna", "terra"]
    assert [attempt.status for attempt in result.attempts] == ["validation_failed", "ok"]


def test_source_context_is_deterministic_bounded_and_does_not_expose_root(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("value = 1\n", encoding="utf-8")
    (src / "helper.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=super-secret-value-123456789\n", encoding="utf-8")

    selector = BoundedSourceContextSelector(max_selected_files=2, max_total_bytes=10_000)
    first = selector.select(tmp_path, objective="change app value", acceptance_texts=("app value changes",))
    second = selector.select(tmp_path, objective="change app value", acceptance_texts=("app value changes",))

    assert first == second
    assert [item.path for item in first.files] == ["src/app.py", "src/helper.py"]
    payload = first.prompt_payload()
    encoded = json.dumps(payload)
    assert str(tmp_path) not in encoded
    assert ".env" not in encoded
    assert "super-secret" not in encoded


def test_source_context_skips_secret_content(tmp_path: Path):
    (tmp_path / "safe.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "unsafe.py").write_text(
        'api_key = "abcdefghijklmnopqrstuvwx"\n', encoding="utf-8"
    )
    snapshot = BoundedSourceContextSelector().select(
        tmp_path,
        objective="change safe value",
        acceptance_texts=("safe value",),
    )
    assert [item.path for item in snapshot.files] == ["safe.py"]
    assert snapshot.excluded_secret_files == 1


def test_ranked_material_file_is_omitted_whole_without_truncation(tmp_path: Path):
    oversized = "x" * 101
    (tmp_path / "app.py").write_text(oversized, encoding="utf-8")
    (tmp_path / "helper.py").write_text("value = 1\n", encoding="utf-8")
    selector = BoundedSourceContextSelector(max_file_bytes=100)

    snapshot = selector.select(
        tmp_path,
        objective="change app helper",
        acceptance_texts=("app helper",),
    )

    assert [item.path for item in snapshot.files] == ["helper.py"]
    assert snapshot.omitted_bounded_files == 1
    assert all(item.size <= selector.max_file_bytes for item in snapshot.files)
    assert oversized not in json.dumps(snapshot.prompt_payload())
