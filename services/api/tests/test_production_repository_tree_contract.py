from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from parallax_api.tools.providers import GitHubTreeEntry, GitHubTreeResult
from parallax_api.tools.providers.github import MAX_TREE_ENTRIES


REPOSITORY = "github:Ryan9876/parallax"
REVISION = "a" * 40
_ALLOWED_FILE_MODES = {"100644", "100755"}


def test_github_tree_result_accepts_exact_capacity_and_rejects_one_over() -> None:
    entries = tuple(
        GitHubTreeEntry(f"capacity/file-{index:04d}.txt", "file", 1, f"{index % 16:x}" * 40)
        for index in range(MAX_TREE_ENTRIES)
    )

    result = GitHubTreeResult(REPOSITORY, REVISION, entries)
    assert len(result.entries) == 1024 == MAX_TREE_ENTRIES

    with pytest.raises(ValueError, match="bounded entry limit"):
        GitHubTreeResult(
            REPOSITORY,
            REVISION,
            entries + (GitHubTreeEntry("capacity/overflow.txt", "file", 1, "f" * 40),),
        )


def test_current_parallax_repository_matches_exact_github_tree_contract() -> None:
    """Exercise the exact entry validation used by production GitHub tree reads.

    The older self-hosting gate checked tracked file bytes but did not construct
    GitHubTreeEntry values. Production validates path, mode, size and entry type
    before the lineage-safe file projection runs, so this gate must do the same.
    """

    root = Path(__file__).resolve().parents[3]
    lines = subprocess.run(
        ["git", "ls-tree", "-r", "-t", "-l", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert len(lines) <= MAX_TREE_ENTRIES, (
        f"tracked repository tree has {len(lines)} entries; protected provider limit is {MAX_TREE_ENTRIES}"
    )

    entries: list[GitHubTreeEntry] = []
    rejected: list[str] = []
    for line in lines:
        metadata, separator, path = line.partition("\t")
        assert separator and path
        fields = metadata.split()
        assert len(fields) == 4, (line, fields)
        mode, kind, object_revision, size_text = fields

        try:
            if kind == "tree":
                if mode != "040000":
                    rejected.append(f"{path}:UNSUPPORTED_TREE_MODE:{mode}")
                    continue
                entries.append(GitHubTreeEntry(path, "tree", 0, object_revision))
                continue
            if kind == "blob":
                if mode not in _ALLOWED_FILE_MODES:
                    rejected.append(f"{path}:UNSUPPORTED_BLOB_MODE:{mode}")
                    continue
                entries.append(GitHubTreeEntry(path, "file", int(size_text), object_revision))
                continue
            rejected.append(f"{path}:UNSUPPORTED_SOURCE_ENTRY:{kind}:{mode}")
        except (TypeError, ValueError) as exc:
            rejected.append(f"{path}:{type(exc).__name__}:{exc}")

    assert rejected == [], "production GitHub tree contract rejects tracked entries: " + ", ".join(rejected)
    GitHubTreeResult(REPOSITORY, REVISION, tuple(entries))
