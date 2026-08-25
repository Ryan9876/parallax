from __future__ import annotations

import pytest

from parallax_api.code.source_context import BoundedSourceContextSelector, SourceContextLimitError


def test_oversized_ranked_file_is_omitted_whole_and_selection_continues(tmp_path):
    oversized = tmp_path / "autonomous_correction.py"
    oversized.write_text("autonomous correction runtime\n" * 4, encoding="utf-8")
    proof_dir = tmp_path / "release-proof"
    proof_dir.mkdir()
    eligible = proof_dir / "runtime-proof.txt"
    eligible.write_text("bounded runtime proof\n", encoding="utf-8")

    selector = BoundedSourceContextSelector(
        max_selected_files=4,
        max_file_bytes=32,
        max_total_bytes=96,
        max_scanned_files=10,
    )
    snapshot = selector.select(
        tmp_path,
        objective="autonomous correction runtime proof",
        acceptance_texts=("release proof remains bounded",),
    )

    paths = [item.path for item in snapshot.files]
    assert "autonomous_correction.py" not in paths
    assert "release-proof/runtime-proof.txt" in paths
    assert snapshot.omitted_bounded_files == 1
    assert snapshot.total_bytes == eligible.stat().st_size
    assert all(item.size <= selector.max_file_bytes for item in snapshot.files)
    assert "autonomous correction runtime" not in str(snapshot.prompt_payload())


def test_total_context_budget_still_omits_whole_files(tmp_path):
    (tmp_path / "alpha.py").write_text("a" * 20, encoding="utf-8")
    (tmp_path / "beta.py").write_text("b" * 20, encoding="utf-8")

    selector = BoundedSourceContextSelector(
        max_selected_files=4,
        max_file_bytes=32,
        max_total_bytes=20,
        max_scanned_files=10,
    )
    snapshot = selector.select(tmp_path, objective="", acceptance_texts=())

    assert len(snapshot.files) == 1
    assert snapshot.total_bytes == 20
    assert snapshot.omitted_bounded_files == 1


def test_workspace_scan_limit_remains_fail_closed(tmp_path):
    (tmp_path / "alpha.py").write_text("a", encoding="utf-8")
    (tmp_path / "beta.py").write_text("b", encoding="utf-8")

    selector = BoundedSourceContextSelector(max_scanned_files=1)
    with pytest.raises(SourceContextLimitError, match="source scan limit"):
        selector.select(tmp_path, objective="", acceptance_texts=())
