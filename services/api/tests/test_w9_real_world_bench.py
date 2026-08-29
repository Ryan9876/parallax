from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from parallax_api.evaluation.parallax_bench import (
    BenchmarkCase,
    BenchmarkDimension,
    ParallaxBenchError,
    ProtectedCeiling,
)
from parallax_api.evaluation.real_world_bench import (
    CanonicalAcceptanceCriterion,
    CanonicalWorkSpecificationEvidence,
    REAL_WORLD_TEMPLATE_SCHEMA_VERSION,
    RealWorldObjectiveTemplate,
    bind_real_world_template,
    load_real_world_template,
    safe_real_world_template_json,
    validate_real_world_template_catalog,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "benchmarks" / "parallax-engineering" / "real-world" / "decision-ledger-v1.json"
RUNBOOK = REPO_ROOT / "benchmarks" / "parallax-engineering" / "real-world" / "decision-ledger-v1-runbook.md"
MODULE = REPO_ROOT / "services" / "api" / "parallax_api" / "evaluation" / "real_world_bench.py"
PROJECT = "11111111-1111-4111-8111-111111111111"
SPEC = "22222222-2222-4222-8222-222222222222"
SPEC_DIGEST = "a" * 64
FIXTURE_DIGEST = "15b098df3956ffe71833778e18a301a8e77fae9f37705223256703619f684900"


def _template() -> RealWorldObjectiveTemplate:
    return load_real_world_template(FIXTURE)


def _criteria(*, include_extra: bool = True) -> tuple[CanonicalAcceptanceCriterion, ...]:
    template = _template()
    criteria = [
        CanonicalAcceptanceCriterion(
            acceptance_id=f"AC-{index:02d}",
            text=f"{requirement.requirement_id}: {requirement.outcome}",
        )
        for index, requirement in enumerate(template.requirements, start=1)
    ]
    if include_extra:
        criteria.append(
            CanonicalAcceptanceCriterion(
                acceptance_id="AC-13",
                text="The implementation should remain maintainable and use the simplest architecture that satisfies the approved outcomes.",
            )
        )
    return tuple(criteria)


def _evidence(
    *,
    criteria: tuple[CanonicalAcceptanceCriterion, ...] | None = None,
    status: str = "APPROVED",
    repository_shape: str = "client-web",
) -> CanonicalWorkSpecificationEvidence:
    return CanonicalWorkSpecificationEvidence(
        project_id=PROJECT,
        work_specification_id=SPEC,
        work_specification_revision=3,
        work_specification_digest=SPEC_DIGEST,
        work_specification_status=status,
        acceptance_criteria=criteria or _criteria(),
        repository_shape=repository_shape,
    )


def test_decision_ledger_fixture_is_frozen_bounded_and_deterministic() -> None:
    template = _template()

    assert template.template_id == "decision-ledger"
    assert template.template_version == "1.0.0"
    assert template.repository_shape == "client-web"
    assert template.expected_ceiling is ProtectedCeiling.REVIEW
    assert tuple(item.requirement_id for item in template.requirements) == tuple(
        f"DL-{index:02d}" for index in range(1, 13)
    )
    assert len({item.digest for item in template.requirements}) == 12
    assert template.fixture_digest == FIXTURE_DIGEST
    assert set(template.comparable_dimensions) == set(BenchmarkDimension)

    replay = load_real_world_template(FIXTURE)
    assert replay == template
    assert replay.fixture_digest == template.fixture_digest


def test_fixture_safe_serialization_is_stable_and_contains_no_authority_payload() -> None:
    template = _template()
    payload = json.loads(safe_real_world_template_json(template))

    assert payload["schema_version"] == REAL_WORLD_TEMPLATE_SCHEMA_VERSION
    assert payload["fixture_digest"] == FIXTURE_DIGEST
    assert [item["requirement_id"] for item in payload["requirements"]] == [
        f"DL-{index:02d}" for index in range(1, 13)
    ]

    serialized = safe_real_world_template_json(template).lower()
    for forbidden in (
        "authorization",
        "bearer ",
        "password",
        "private key",
        "chain-of-thought",
        "source_bytes",
        "patch",
        "provider_payload",
        "production_deployment",
    ):
        assert forbidden not in serialized


def test_template_identity_conflicts_fail_closed_and_material_drift_changes_digest() -> None:
    template = _template()
    first = template.requirements[0]
    drifted_requirement = replace(first, outcome=first.outcome + " The record also exposes a stable revision label.")
    drifted = replace(template, requirements=(drifted_requirement, *template.requirements[1:]))

    assert drifted.fixture_digest != template.fixture_digest
    with pytest.raises(ParallaxBenchError, match="identity conflicts with different content"):
        validate_real_world_template_catalog((template, drifted))
    with pytest.raises(ParallaxBenchError, match="identity must be unique"):
        validate_real_world_template_catalog((template, template))


def test_fixture_loader_rejects_requirement_and_fixture_digest_drift(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["requirements"][0]["outcome"] += " drift"
    drifted = tmp_path / "drifted.json"
    drifted.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ParallaxBenchError, match="requirement DL-01 digest mismatch"):
        load_real_world_template(drifted)

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["objective"] += " drift"
    drifted.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ParallaxBenchError, match="fixture digest mismatch"):
        load_real_world_template(drifted)


def test_fixture_loader_rejects_unreviewed_extra_fields(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["reference_solution"] = "hidden"
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ParallaxBenchError, match="unexpected or missing fields"):
        load_real_world_template(path)


def test_canonical_binding_produces_existing_benchmark_case_with_complete_acceptance_identity() -> None:
    template = _template()
    evidence = _evidence()
    case = bind_real_world_template(template, evidence)

    assert isinstance(case, BenchmarkCase)
    assert case.case_id == template.template_id
    assert case.case_version == template.template_version
    assert case.objective_class == template.objective_class
    assert case.project_id == PROJECT
    assert case.work_specification_id == SPEC
    assert case.work_specification_revision == 3
    assert case.work_specification_digest == SPEC_DIGEST
    assert case.acceptance_ids == tuple(f"AC-{index:02d}" for index in range(1, 14))
    assert case.repository_shape == template.repository_shape
    assert case.comparable_dimensions == template.comparable_dimensions
    assert case.expected_ceiling is ProtectedCeiling.REVIEW
    assert case.fixture_digest == template.fixture_digest


def test_binding_requires_every_frozen_requirement_token_exactly_once() -> None:
    template = _template()
    criteria = list(_criteria())
    criteria[0] = replace(criteria[0], text=template.requirements[0].outcome)

    with pytest.raises(ParallaxBenchError, match=r"DL-01.*observed 0"):
        bind_real_world_template(template, _evidence(criteria=tuple(criteria)))

    criteria = list(_criteria())
    criteria[0] = replace(criteria[0], text=criteria[0].text + " Also preserve DL-02 explicitly.")
    with pytest.raises(ParallaxBenchError, match=r"DL-02.*observed 2"):
        bind_real_world_template(template, _evidence(criteria=tuple(criteria)))


def test_semantic_similarity_never_substitutes_for_missing_token_coverage() -> None:
    template = _template()
    criteria = list(_criteria())
    criteria[0] = CanonicalAcceptanceCriterion(
        acceptance_id="AC-01",
        text="Users can create, view, edit and delete decision records.",
    )

    with pytest.raises(ParallaxBenchError, match="DL-01"):
        bind_real_world_template(template, _evidence(criteria=tuple(criteria)))


def test_binding_requires_approved_unique_canonical_work_spec_identity() -> None:
    with pytest.raises(ParallaxBenchError, match="requires an APPROVED Work Specification"):
        _evidence(status="DRAFT")

    criteria = list(_criteria())
    criteria[-1] = replace(criteria[-1], acceptance_id="AC-12")
    with pytest.raises(ParallaxBenchError, match="acceptance IDs must be unique"):
        _evidence(criteria=tuple(criteria))

    with pytest.raises(ParallaxBenchError, match="work_specification_revision"):
        replace(_evidence(), work_specification_revision=0)

    with pytest.raises(ParallaxBenchError, match="work_specification_digest"):
        replace(_evidence(), work_specification_digest="not-a-digest")


def test_repository_shape_mismatch_fails_closed() -> None:
    with pytest.raises(ParallaxBenchError, match="repository shape does not match"):
        bind_real_world_template(_template(), _evidence(repository_shape="service"))


def test_runtime_provider_source_and_client_paths_do_not_reference_benchmark_identity() -> None:
    api_root = REPO_ROOT / "services" / "api" / "parallax_api"
    for path in api_root.rglob("*.py"):
        if "evaluation" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "decision-ledger" not in text, path
        assert "p2-v0.23.0" not in text, path
        assert "real_world_bench" not in text, path

    client_root = REPO_ROOT / "apps" / "client" / "src"
    for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx"):
        for path in client_root.rglob(pattern):
            text = path.read_text(encoding="utf-8").lower()
            assert "decision-ledger" not in text, path
            assert "p2-v0.23.0" not in text, path
            assert "real_world_bench" not in text, path


def test_real_world_extension_has_no_runtime_or_provider_authority_imports() -> None:
    source = MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "EngineeringRunService",
        "ProviderGateway",
        "production_source_delivery",
        "production_source_bootstrap",
        "GitHubProvider",
        "Vercel",
        "merge_pull_request",
        "promote",
    ):
        assert forbidden not in source


def test_benchmark_fixture_directory_contains_no_reference_implementation_source() -> None:
    fixture_dir = FIXTURE.parent
    assert RUNBOOK.exists()
    assert {path.suffix for path in fixture_dir.iterdir() if path.is_file()} <= {".json", ".md"}
    assert not any(path.suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css"} for path in fixture_dir.rglob("*"))

    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "OUT_OF_BAND_SOURCE_EDIT" in runbook
    assert "PRE_APPROVAL_CLARIFICATION" in runbook
    assert "POST_APPROVAL_CORRECTION" in runbook
    assert "EXPLICIT_RETRY_RECOVERY" in runbook
    assert "Preview is the autonomous publication ceiling" in runbook
