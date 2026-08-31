from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from parallax_api.code.agentic_candidate_recovery import (
    FINAL_VALIDATOR_REPAIR_GUIDANCE,
    MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
    VALIDATOR_REPAIR_GUIDANCE,
)
from parallax_api.code.patching import EMPTY_SHA256, PatchError, SourcePatch, TextPatchEngine
from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    GeneratedFileContent,
    ImplementationContentProposal,
    ImplementationProposal,
    ModelOutputValidationError,
    canonicalize_content_proposal,
    render_content_unified_diff,
)


def _snapshot(path: str | None = "app.py", content: str = "old\n") -> SourceContextSnapshot:
    files = ()
    total = 0
    if path is not None:
        encoded = content.encode("utf-8")
        files = (SourceContextFile(path, sha256(encoded).hexdigest(), len(encoded), content),)
        total = len(encoded)
    return SourceContextSnapshot(
        files=files,
        digest=sha256(b"p2326-source").hexdigest(),
        total_bytes=total,
        excluded_secret_files=0,
        omitted_bounded_files=0,
    )


def _source_patch(proposal: ImplementationProposal) -> SourcePatch:
    item = proposal.patches[0]
    return SourcePatch(
        path=item.path,
        expected_base_sha256=item.expected_base_sha256,
        unified_diff=item.unified_diff,
    )


def test_existing_file_intent_binds_protected_sha_and_round_trips(tmp_path: Path):
    source = _snapshot()
    proposal = canonicalize_content_proposal(
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[GeneratedFileContent(path="app.py", content="new\n")],
        ),
        source,
    )

    assert proposal.patches[0].expected_base_sha256 == source.files[0].sha256
    assert proposal.patches[0].unified_diff.startswith("--- a/app.py\n+++ b/app.py\n")

    (tmp_path / "app.py").write_text("old\n")
    prepared = TextPatchEngine().prepare(tmp_path, _source_patch(proposal))
    assert prepared.after == b"new\n"


def test_new_nested_file_intent_uses_empty_base_and_existing_safe_engine(tmp_path: Path):
    proposal = canonicalize_content_proposal(
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[
                GeneratedFileContent(
                    path="prototypes/fml-data-readiness/index.html",
                    content="<main>ready</main>\n",
                )
            ],
        ),
        _snapshot(path=None),
    )
    patch = proposal.patches[0]
    assert patch.expected_base_sha256 == EMPTY_SHA256
    assert patch.unified_diff.startswith(
        "--- /dev/null\n+++ b/prototypes/fml-data-readiness/index.html\n"
    )

    engine = TextPatchEngine()
    prepared = engine.prepare(tmp_path, _source_patch(proposal))
    assert not (tmp_path / "prototypes").exists()
    engine.commit(tmp_path, prepared)
    assert (tmp_path / "prototypes/fml-data-readiness/index.html").read_text() == "<main>ready</main>\n"


def test_duplicate_and_noop_content_intents_fail_closed():
    with pytest.raises(ValidationError):
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[
                GeneratedFileContent(path="app.py", content="one\n"),
                GeneratedFileContent(path="app.py", content="two\n"),
            ],
        )

    with pytest.raises(ModelOutputValidationError):
        canonicalize_content_proposal(
            ImplementationContentProposal(
                acceptance_ids_covered=["AC-01"],
                files=[GeneratedFileContent(path="app.py", content="old\n")],
            ),
            _snapshot(),
        )


def test_unselected_existing_file_collision_remains_safe_engine_rejection(tmp_path: Path):
    (tmp_path / "app.py").write_text("existing\n")
    proposal = canonicalize_content_proposal(
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[GeneratedFileContent(path="app.py", content="changed\n")],
        ),
        _snapshot(path=None),
    )
    with pytest.raises(PatchError):
        TextPatchEngine().prepare(tmp_path, _source_patch(proposal))


def test_renderer_preserves_trailing_newline_semantics_and_is_deterministic(tmp_path: Path):
    cases = [
        ("old\n", "new\n"),
        ("old", "new"),
        ("old\n", "new"),
        ("old", "new\n"),
    ]
    for index, (before, after) in enumerate(cases):
        path = f"case{index}.txt"
        first = render_content_unified_diff(path=path, before=before, after=after, creating=False)
        second = render_content_unified_diff(path=path, before=before, after=after, creating=False)
        assert first == second
        target = tmp_path / path
        target.write_text(before, newline="")
        patch = SourcePatch(
            path=path,
            expected_base_sha256=sha256(before.encode()).hexdigest(),
            unified_diff=first,
        )
        prepared = TextPatchEngine().prepare(tmp_path, patch)
        assert prepared.after.decode("utf-8") == after


def test_model_visible_content_schema_has_no_patch_authority():
    assert set(GeneratedFileContent.model_fields) == {"path", "content"}
    assert set(ImplementationContentProposal.model_fields) == {"acceptance_ids_covered", "files"}


def test_validator_repair_guidance_is_semantic_and_retry_budget_unchanged():
    joined = f"{VALIDATOR_REPAIR_GUIDANCE} {FINAL_VALIDATOR_REPAIR_GUIDANCE}"
    assert "complete desired" in joined
    assert "server" in joined.casefold()
    assert "source-digest binding" in joined
    assert "hunk coordinates" not in joined
    assert MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT == 1
