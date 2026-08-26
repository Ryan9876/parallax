from __future__ import annotations

from hashlib import sha256
import json

import pytest

from parallax_api.code.repository_intelligence import (
    RepositoryEvidenceEntry,
    RepositoryEvidenceSnapshot,
    RepositoryIntelligenceAnalyzer,
    RepositoryShape,
    RepositorySourceIdentity,
)
from parallax_api.code.validated_memory import (
    MemoryAdmissionPolicy,
    MemoryFailureCode,
    MemoryKind,
    MemoryProvenance,
    MemoryReuseRequest,
    MemoryScope,
    MemorySelectionStatus,
    MemorySignalRequirement,
    SharedMemoryApproval,
    ValidatedMemoryError,
    ValidatedMemoryItem,
    ValidatedMemoryRegistry,
    ValidatedMemorySelector,
    public_selection_field_names,
)

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_WORK_SPEC_ID = "33333333-3333-4333-8333-333333333333"
CURRENT_WORK_SPEC_ID = "44444444-4444-4444-8444-444444444444"
REVISION = "f" * 40
OTHER_REVISION = "1" * 40
WORK_SPEC_DIGEST = "a" * 64
CURRENT_WORK_SPEC_DIGEST = "b" * 64
VALIDATION_DIGEST = "c" * 64
EVALUATOR_DIGEST = "d" * 64
OTHER_EVALUATOR_DIGEST = "e" * 64
ACCEPTANCE_IDS = ("AC-01", "AC-02", "AC-03")


def _entry(path: str, content: str = "") -> RepositoryEvidenceEntry:
    payload = content.encode()
    return RepositoryEvidenceEntry(path, sha256(payload).hexdigest(), len(payload), payload)


def _profile(shape: RepositoryShape = RepositoryShape.SINGLE_PACKAGE, *, project_id: str = PROJECT_ID, revision: str = REVISION):
    identity = RepositorySourceIdentity(project_id, "ExampleOrg/example-app", revision)
    if shape is RepositoryShape.SINGLE_PACKAGE:
        entries = (
            _entry("package.json", json.dumps({"dependencies": {"react": "latest", "vite": "latest"}})),
            _entry("src/main.tsx"),
        )
    elif shape is RepositoryShape.PYTHON_SERVICE:
        entries = (
            _entry("pyproject.toml", "[project]\nname='api'\ndependencies=['fastapi','pytest']\n"),
            _entry("src/service.py"),
        )
    elif shape is RepositoryShape.UNSUPPORTED:
        entries = (_entry("Cargo.toml", "[package]\nname='x'\n"), _entry("src/main.rs"))
    else:
        entries = (_entry("index.html", "<main></main>"), _entry("styles/site.css"))
    return RepositoryIntelligenceAnalyzer(identity).analyze(RepositoryEvidenceSnapshot(identity, entries))


def _provenance(profile=None, *, evaluator_digest: str = EVALUATOR_DIGEST) -> MemoryProvenance:
    profile = profile or _profile()
    return MemoryProvenance.from_compatibility_profile(
        profile=profile,
        work_specification_id=SOURCE_WORK_SPEC_ID,
        work_specification_revision=2,
        work_specification_digest=WORK_SPEC_DIGEST,
        acceptance_ids=ACCEPTANCE_IDS,
        validation_evidence_digest=VALIDATION_DIGEST,
        evaluator_policy_digest=evaluator_digest,
    )


def _item(*, memory_id: str = "pattern.safe-form", kind: MemoryKind = MemoryKind.IMPLEMENTATION_PATTERN, scope: MemoryScope = MemoryScope.PROJECT_PRIVATE, profile=None, evaluator_digest: str = EVALUATOR_DIGEST, shapes=None, signals=(), content=("Apply the bounded accepted implementation pattern.",)) -> ValidatedMemoryItem:
    profile = profile or _profile()
    return ValidatedMemoryItem(
        memory_id=memory_id,
        version="1.0.0",
        kind=kind,
        scope=scope,
        provenance=_provenance(profile, evaluator_digest=evaluator_digest),
        objective_kinds=("implement-feature",),
        compatible_shapes=tuple(shapes or (profile.repository_shape,)),
        required_signals=tuple(signals),
        content=tuple(content),
    )


def _policy(*items: ValidatedMemoryItem) -> MemoryAdmissionPolicy:
    approvals = tuple(SharedMemoryApproval(item.memory_id, item.version, item.digest) for item in items if item.scope is MemoryScope.SANITIZED_SHARED)
    return MemoryAdmissionPolicy(shared_approvals=approvals)


def _registry(*items: ValidatedMemoryItem) -> ValidatedMemoryRegistry:
    registry = ValidatedMemoryRegistry(_policy(*items))
    for item in items:
        registry.admit(item)
    return registry


def _request(profile=None, *, project_id: str = PROJECT_ID, evaluator_digest: str = EVALUATOR_DIGEST, work_spec_digest: str = CURRENT_WORK_SPEC_DIGEST, requested_kinds=tuple(MemoryKind)) -> MemoryReuseRequest:
    profile = profile or _profile(project_id=project_id)
    return MemoryReuseRequest(
        requester_project_id=project_id,
        compatibility=profile,
        objective_kind="implement-feature",
        work_specification_id=CURRENT_WORK_SPEC_ID,
        work_specification_revision=7,
        work_specification_digest=work_spec_digest,
        acceptance_ids=ACCEPTANCE_IDS,
        evaluator_policy_digest=evaluator_digest,
        requested_kinds=tuple(requested_kinds),
    )


def _rejection_codes(result) -> set[MemoryFailureCode]:
    return {item.code for item in result.rejections}


def test_private_admission_is_idempotent_and_version_conflict_is_immutable() -> None:
    approved = _item(memory_id="pattern.private")
    changed = ValidatedMemoryItem(
        memory_id=approved.memory_id,
        version=approved.version,
        kind=approved.kind,
        scope=approved.scope,
        provenance=approved.provenance,
        objective_kinds=approved.objective_kinds,
        compatible_shapes=approved.compatible_shapes,
        content=("Apply a different bounded pattern.",),
    )
    registry = ValidatedMemoryRegistry(_policy(approved))
    first = registry.admit(approved)
    assert registry.admit(approved) is first
    with pytest.raises(ValidatedMemoryError) as exc:
        registry.admit(changed)
    assert exc.value.code is MemoryFailureCode.MEMORY_VERSION_CONFLICT
    assert registry.registered() == (first,)


def test_shared_memory_requires_exact_server_owned_digest_approval() -> None:
    shared = _item(memory_id="pattern.shared", scope=MemoryScope.SANITIZED_SHARED, content=("Use an accessibility-first form validation pattern.",))
    assert ValidatedMemoryRegistry(_policy(shared)).admit(shared).content_digest == shared.digest
    with pytest.raises(ValidatedMemoryError) as exc:
        ValidatedMemoryRegistry(MemoryAdmissionPolicy()).admit(shared)
    assert exc.value.code is MemoryFailureCode.SHARED_MEMORY_NOT_APPROVED


def test_foreign_private_memory_is_completely_invisible() -> None:
    foreign_profile = _profile(project_id=OTHER_PROJECT_ID)
    private = _item(memory_id="pattern.foreign", profile=foreign_profile)
    result = ValidatedMemorySelector(_registry(private)).select(_request())
    assert result.status is MemorySelectionStatus.MISS
    assert result.visible_candidate_count == 0
    assert result.rejections == ()
    payload = repr(result.as_dict())
    assert OTHER_PROJECT_ID not in payload
    assert foreign_profile.repository_ref_digest not in payload
    assert foreign_profile.source_revision not in payload


def test_cross_project_sanitized_shared_pattern_is_safe_hit() -> None:
    source_profile = _profile(project_id=OTHER_PROJECT_ID)
    shared = _item(
        memory_id="pattern.cross-project",
        scope=MemoryScope.SANITIZED_SHARED,
        profile=source_profile,
        shapes=(RepositoryShape.SINGLE_PACKAGE,),
        signals=(MemorySignalRequirement("framework", "react"),),
        content=("Prefer explicit accessible labels and deterministic validation.",),
    )
    result = ValidatedMemorySelector(_registry(shared)).select(_request())
    assert result.status is MemorySelectionStatus.HIT
    assert result.eligible_hit_count == 1
    assert result.candidates[0].fresh_validation_required is True
    payload = repr(result.as_dict())
    assert OTHER_PROJECT_ID not in payload
    assert source_profile.repository_ref_digest not in payload
    assert source_profile.source_revision not in payload
    assert SOURCE_WORK_SPEC_ID not in payload
    assert result.as_dict()["grants_authority"] is False


def test_compatibility_fact_requires_exact_current_source_and_profile() -> None:
    source = _profile()
    fact = _item(memory_id="fact.compatibility", kind=MemoryKind.COMPATIBILITY_FACT, profile=source, content=("Repository shape is a validated single package.",))
    selector = ValidatedMemorySelector(_registry(fact))
    assert selector.select(_request(source)).status is MemorySelectionStatus.HIT
    stale = selector.select(_request(_profile(revision=OTHER_REVISION)))
    assert stale.status is MemorySelectionStatus.MISS
    assert MemoryFailureCode.STALE_COMPATIBILITY_EVIDENCE in _rejection_codes(stale)


def test_shape_signal_and_evaluator_drift_fail_closed() -> None:
    source = _profile()
    pattern = _item(memory_id="pattern.constraints", profile=source, shapes=(RepositoryShape.SINGLE_PACKAGE,), signals=(MemorySignalRequirement("framework", "react"),))
    selector = ValidatedMemorySelector(_registry(pattern))
    assert selector.select(_request(source)).status is MemorySelectionStatus.HIT
    wrong_shape = selector.select(_request(_profile(RepositoryShape.PYTHON_SERVICE)))
    assert MemoryFailureCode.INCOMPATIBLE_REPOSITORY_SHAPE in _rejection_codes(wrong_shape)
    stale_policy = selector.select(_request(source, evaluator_digest=OTHER_EVALUATOR_DIGEST))
    assert MemoryFailureCode.VALIDATION_POLICY_STALE in _rejection_codes(stale_policy)


def test_foreign_private_items_do_not_fingerprint_visible_result() -> None:
    visible = _item(memory_id="pattern.visible")
    foreign = _item(memory_id="pattern.private-foreign", profile=_profile(project_id=OTHER_PROJECT_ID))
    baseline = ValidatedMemorySelector(_registry(visible)).select(_request())
    with_foreign = ValidatedMemorySelector(_registry(visible, foreign)).select(_request())
    assert baseline.visible_registry_digest == with_foreign.visible_registry_digest
    assert baseline.selection_id == with_foreign.selection_id
    assert baseline.visible_candidate_count == with_foreign.visible_candidate_count == 1


def test_replay_order_and_current_validation_requirements_are_stable() -> None:
    one = _item(memory_id="pattern.one")
    two = _item(memory_id="pattern.two")
    policy = _policy(one, two)
    first = ValidatedMemoryRegistry(policy)
    second = ValidatedMemoryRegistry(policy)
    first.admit(one); first.admit(two)
    second.admit(two); second.admit(one)
    request = _request()
    left = ValidatedMemorySelector(first).select(request)
    right = ValidatedMemorySelector(second).select(request)
    assert left == right
    assert left.selection_id.startswith("memsel:")
    assert left.fresh_validation_required is True
    assert [item.memory_id for item in left.candidates] == ["pattern.one", "pattern.two"]


def test_hit_and_miss_keep_identical_current_validation_requirements() -> None:
    selector = ValidatedMemorySelector(_registry(_item()))
    hit = selector.select(_request())
    miss = selector.select(_request(requested_kinds=(MemoryKind.VALIDATION_EVIDENCE,)))
    assert hit.status is MemorySelectionStatus.HIT
    assert miss.status is MemorySelectionStatus.MISS
    assert hit.current_evaluator_policy_digest == miss.current_evaluator_policy_digest
    assert hit.current_work_specification_digest == miss.current_work_specification_digest
    assert hit.fresh_validation_required is miss.fresh_validation_required is True
    assert hit.as_dict()["grants_authority"] is False
    assert miss.as_dict()["grants_authority"] is False


def test_public_selection_contract_excludes_private_and_authority_surfaces() -> None:
    names = set(public_selection_field_names())
    forbidden = {
        "source_project_id", "source_repository_ref_digest", "source_revision",
        "source_identity_digest", "compatibility_profile_digest", "work_specification_id",
        "acceptance_ids", "secret_value", "secret_handle", "provider_payload",
        "command", "deployment_target", "tool_grant", "service_binding_grant",
    }
    assert names.isdisjoint(forbidden)
    payload = ValidatedMemorySelector(_registry(_item())).select(_request()).as_dict()
    for key in (
        "contains_private_cross_project_metadata", "contains_raw_source", "contains_prompt",
        "contains_secret_values", "contains_secret_handles", "contains_provider_payload",
        "grants_tools", "grants_service_bindings", "grants_provider_scope", "grants_approval",
        "performs_source_mutation", "performs_execution", "performs_deployment", "grants_authority",
    ):
        assert payload[key] is False


def test_memory_layer_does_not_mutate_s1_or_expose_runtime_authority_api() -> None:
    profile = _profile()
    before = profile.as_dict()
    registry = _registry(_item(profile=profile))
    selector = ValidatedMemorySelector(registry)
    selector.select(_request(profile))
    assert profile.as_dict() == before
    assert {name for name in dir(registry) if not name.startswith("_")} == {"admit", "digest", "policy", "registered"}
    assert {name for name in dir(selector) if not name.startswith("_")} == {"registry", "select"}
