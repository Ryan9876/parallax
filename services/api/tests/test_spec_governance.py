from __future__ import annotations

from pathlib import Path

from parallax_api.intelligence.protected_metrics import evaluate_spec_contract


def test_all_versioned_parallax_specs_pass_protected_contract():
    repository_root = Path(__file__).resolve().parents[3]
    specs = sorted((repository_root / "specs").glob("P2-V*.md"))
    assert specs, "no versioned Parallax specifications found"

    failures: list[str] = []
    for path in specs:
        result = evaluate_spec_contract(path.read_text(encoding="utf-8"))
        if not result.passed:
            failures.append(f"{path.name}: {', '.join(result.failures)}")

    assert not failures, "\n".join(failures)
