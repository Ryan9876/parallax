from __future__ import annotations

from pathlib import Path
import re

from parallax_api.tools.providers.github import MAX_TREE_ENTRIES


API_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHTS = (
    API_ROOT / "scripts" / "production_provider_preflight.py",
    API_ROOT / "scripts" / "production_projected_source_preflight.py",
    API_ROOT / "scripts" / "production_lineage_composition_preflight.py",
)
BOUND = re.compile(r"^_MAX_TREE_ENTRIES = (\d+)$", re.MULTILINE)


def _tree_bound(path: Path) -> int:
    match = BOUND.search(path.read_text(encoding="utf-8"))
    assert match is not None, f"{path.name} must declare an explicit protected tree-entry bound"
    return int(match.group(1))


def test_production_preflight_tree_bounds_match_runtime_provider_contract() -> None:
    # Production release gates must track the server-owned provider capacity;
    # a stale stricter copy can block a valid runtime release before cutover.
    assert MAX_TREE_ENTRIES == 1024
    assert {_tree_bound(path) for path in PREFLIGHTS} == {MAX_TREE_ENTRIES}
