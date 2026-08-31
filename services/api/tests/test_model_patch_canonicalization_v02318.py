from __future__ import annotations

from hashlib import sha256

import pytest

from parallax_api.code.implementation import ImplementationRequest, SafeImplementationEngine
from parallax_api.code.patching import (
    EMPTY_SHA256,
    PatchConflictError,
    SourcePatch,
    StaleBaseError,
    UnsafeTargetError,
)


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _request(path: str, before: str, diff: str, *, digest: str | None = None) -> ImplementationRequest:
    return ImplementationRequest(
        patches=(
            SourcePatch(
                path=path,
                expected_base_sha256=digest or _digest(before),
                unified_diff=diff,
            ),
        )
    )


def test_strict_valid_patch_remains_unchanged(tmp_path):
    before = "alpha\nbeta\ngamma\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- a/sample.txt
+++ b/sample.txt
@@ -1,3 +1,3 @@
 alpha
-beta
+BETA
 gamma
"""

    result = SafeImplementationEngine().apply(tmp_path, _request("sample.txt", before, diff))

    assert target.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"
    assert result["patches"][0]["unified_diff"] == diff


def test_wrong_hunk_counts_and_positions_are_canonicalized_from_exact_source(tmp_path):
    before = "alpha\nbeta\ngamma\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- sample.txt
+++ sample.txt
@@ -99,9 +42,17 @@
 alpha
-beta
+BETA
 gamma
"""

    result = SafeImplementationEngine().apply(tmp_path, _request("sample.txt", before, diff))

    assert target.read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"
    canonical = result["patches"][0]["unified_diff"]
    assert canonical.startswith("--- a/sample.txt\n+++ b/sample.txt\n@@ -1,3 +1,3 @@\n")


def test_declared_exact_position_disambiguates_repeated_source(tmp_path):
    before = "same\nleft\nsame\nright\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- a/sample.txt
+++ b/sample.txt
@@ -3,99 +80,99 @@
-same
+chosen
"""

    SafeImplementationEngine().apply(tmp_path, _request("sample.txt", before, diff))

    assert target.read_text(encoding="utf-8") == "same\nleft\nchosen\nright\n"


def test_wrong_position_with_multiple_exact_matches_is_rejected(tmp_path):
    before = "same\nleft\nsame\nright\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- a/sample.txt
+++ b/sample.txt
@@ -2,7 +20,7 @@
-same
+chosen
"""

    with pytest.raises(PatchConflictError):
        SafeImplementationEngine().validate(tmp_path, _request("sample.txt", before, diff))

    assert target.read_text(encoding="utf-8") == before


def test_pure_insertion_remains_coordinate_anchored(tmp_path):
    before = "alpha\nbeta\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- a/sample.txt
+++ b/sample.txt
@@ -1,8 +99,12 @@
+inserted
"""

    SafeImplementationEngine().apply(tmp_path, _request("sample.txt", before, diff))

    assert target.read_text(encoding="utf-8") == "alpha\ninserted\nbeta\n"


def test_pure_insertion_outside_source_is_rejected(tmp_path):
    before = "alpha\nbeta\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- a/sample.txt
+++ b/sample.txt
@@ -9,8 +99,12 @@
+inserted
"""

    with pytest.raises(PatchConflictError):
        SafeImplementationEngine().validate(tmp_path, _request("sample.txt", before, diff))


def test_new_file_git_prologue_and_bad_counts_are_canonicalized(tmp_path):
    diff = """diff --git a/PARALLAX_QA.md b/PARALLAX_QA.md
new file mode 100644
--- /dev/null
+++ b/PARALLAX_QA.md
@@ -5,9 +44,20 @@
+QA fixture
+bounded change
"""
    request = _request(
        "PARALLAX_QA.md",
        "",
        diff,
        digest=EMPTY_SHA256,
    )

    result = SafeImplementationEngine().apply(tmp_path, request)

    assert (tmp_path / "PARALLAX_QA.md").read_text(encoding="utf-8") == "QA fixture\nbounded change\n"
    canonical = result["patches"][0]["unified_diff"]
    assert canonical.startswith("--- /dev/null\n+++ b/PARALLAX_QA.md\n@@ -0,0 +1,2 @@\n")


def test_stale_expected_base_digest_is_never_rebound(tmp_path):
    before = "alpha\nbeta\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- sample.txt
+++ sample.txt
@@ -99,7 +40,7 @@
-alpha
+ALPHA
"""

    with pytest.raises(StaleBaseError):
        SafeImplementationEngine().validate(
            tmp_path,
            _request("sample.txt", before, diff, digest="0" * 64),
        )


def test_exact_source_mismatch_is_not_fuzzed(tmp_path):
    before = "alpha\nbeta\ngamma\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- a/sample.txt
+++ b/sample.txt
@@ -88,9 +20,9 @@
-not-beta
+BETA
"""

    with pytest.raises(PatchConflictError):
        SafeImplementationEngine().validate(tmp_path, _request("sample.txt", before, diff))


def test_unsafe_target_remains_rejected_before_canonicalization(tmp_path):
    diff = """--- /dev/null
+++ b/.env
@@ -0,0 +1,1 @@
+SAFE_LOOKING=value
"""

    with pytest.raises(UnsafeTargetError):
        SafeImplementationEngine().validate(
            tmp_path,
            _request(".env", "", diff, digest=EMPTY_SHA256),
        )


def test_multiple_hunks_relocate_only_forward_without_overlap(tmp_path):
    before = "one\ntwo\nthree\nfour\nfive\n"
    target = tmp_path / "sample.txt"
    target.write_text(before, encoding="utf-8")
    diff = """--- sample.txt
+++ sample.txt
@@ -50,7 +90,8 @@
-two
+TWO
@@ -70,11 +120,12 @@
-four
+FOUR
"""

    SafeImplementationEngine().apply(tmp_path, _request("sample.txt", before, diff))

    assert target.read_text(encoding="utf-8") == "one\nTWO\nthree\nFOUR\nfive\n"
