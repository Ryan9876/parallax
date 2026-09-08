from __future__ import annotations

from parallax_api.intelligence.offline_intelligence import (
    canonical_offline_digest,
    compile_spec_offline,
)


CONTRACT = (
    {"id": "AC-01", "title": "One", "protected_requirement": "Preserve architecture."},
    {"id": "AC-02", "title": "Two", "protected_requirement": "Preserve schema."},
    {"id": "AC-03", "title": "Three", "protected_requirement": "Preserve data."},
    {"id": "AC-04", "title": "Four", "protected_requirement": "Optimize repositories."},
    {"id": "AC-05", "title": "Five", "protected_requirement": "Measure latency."},
    {"id": "AC-06", "title": "Six", "protected_requirement": "Protect leases."},
    {"id": "AC-07", "title": "Seven", "protected_requirement": "Cache is derived only."},
    {"id": "AC-08", "title": "Eight", "protected_requirement": "Narrow execution."},
)


def test_offline_spec_compiler_is_deterministic_and_explicitly_development_only() -> None:
    first = compile_spec_offline("# P2-V0.24.0\nApproved.", CONTRACT)
    second = compile_spec_offline("# P2-V0.24.0\nApproved.", CONTRACT)
    assert first == second
    assert canonical_offline_digest(first) == canonical_offline_digest(second)
    assert first.program_version == "offline-spec-compiler-v1"
    assert set(first.plan) == {
        "architecture_decisions",
        "work_items",
        "validations",
        "risks",
    }
    assert all(first.plan.values())
    assert "not implied" in first.critique[0]


def test_offline_compiler_changes_identity_when_spec_changes() -> None:
    first = compile_spec_offline("# A", CONTRACT)
    second = compile_spec_offline("# B", CONTRACT)
    assert canonical_offline_digest(first) != canonical_offline_digest(second)
