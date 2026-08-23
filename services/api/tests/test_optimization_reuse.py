import pytest

from parallax_api.code.optimization_controller import (
    AdaptiveModelRouter,
    FailureFingerprint,
    ModelClass,
    ModelProfile,
    OptimizationPolicyError,
    RepairMemory,
    RepairMemoryRecord,
    ReusablePatternRecord,
    ReusablePatternRegistry,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


def test_pattern_registry_and_repair_memory_are_validated_and_project_isolated() -> None:
    private = ReusablePatternRecord(
        pattern_id="pattern:api-service", version="v1", digest=D1, pattern_type="python:service",
        compatibility=("python:3.13", "fastapi"), evidence_refs=("test:pattern-private",),
        validated=True, project_id="project:one",
    )
    public = ReusablePatternRecord(
        pattern_id="pattern:public-config", version="v1", digest=D2, pattern_type="python:service",
        compatibility=("python:3.13", "fastapi"), evidence_refs=("test:pattern-public",),
        validated=True, public=True,
    )
    unvalidated = ReusablePatternRecord(
        pattern_id="pattern:untested", version="v1", digest=D3, pattern_type="python:service",
        compatibility=("python:3.13",), evidence_refs=(), validated=False, project_id="project:one",
    )
    registry = ReusablePatternRegistry((private, public, unvalidated))
    assert {item.pattern_id for item in registry.recommend(project_id="project:one", pattern_type="python:service", compatibility=("python:3.13",))} == {
        "pattern:api-service", "pattern:public-config"
    }
    assert [item.pattern_id for item in registry.recommend(project_id="project:two", pattern_type="python:service", compatibility=("python:3.13",))] == ["pattern:public-config"]

    fingerprint = FailureFingerprint.build(
        failure_class="TEST", failure_code="ASSERTION_FAILED", component_id="api:worker",
        structural_locator="test:worker-recovery", tool_identity="pytest",
    )
    memory = RepairMemory((
        RepairMemoryRecord(
            fingerprint=fingerprint.digest, repair_class="repair:lease-check", outcome_quality="passed",
            compatibility=("python:3.13",), evidence_refs=("test:repair-private",), project_id="project:one",
        ),
        RepairMemoryRecord(
            fingerprint=fingerprint.digest, repair_class="repair:public-normalization", outcome_quality="passed",
            compatibility=("python:3.13",), evidence_refs=("test:repair-public",), public=True,
        ),
    ))
    assert {item.repair_class for item in memory.recommend(project_id="project:one", fingerprint=fingerprint.digest, compatibility=("python:3.13",))} == {
        "repair:lease-check", "repair:public-normalization"
    }
    assert [item.repair_class for item in memory.recommend(project_id="project:two", fingerprint=fingerprint.digest, compatibility=("python:3.13",))] == ["repair:public-normalization"]

    with pytest.raises(OptimizationPolicyError):
        FailureFingerprint.build(
            failure_class="TEST", failure_code="ASSERTION_FAILED", component_id="api:worker",
            structural_locator="authorization:abcdefgh", tool_identity="pytest",
        )


def test_model_routing_escalates_without_changing_authority_and_blocks_missing_capability() -> None:
    router = AdaptiveModelRouter((
        ModelProfile(ModelClass.FAST, ("format",)),
        ModelProfile(ModelClass.GENERAL, ("format", "code")),
        ModelProfile(ModelClass.DEEP, ("code", "architecture")),
    ), escalation_confidence=0.65)
    routine = router.route(required_capability="code", evidence_confidence=0.9, approved_classes=(ModelClass.GENERAL, ModelClass.DEEP))
    assert routine.model_class is ModelClass.GENERAL and routine.blocked is False
    uncertain = router.route(required_capability="code", evidence_confidence=0.4, approved_classes=(ModelClass.GENERAL, ModelClass.DEEP))
    assert uncertain.model_class is ModelClass.DEEP
    protected = router.route(required_capability="code", evidence_confidence=0.99, approved_classes=(ModelClass.GENERAL, ModelClass.DEEP), protected_work=True)
    assert protected.model_class is ModelClass.DEEP
    blocked = router.route(required_capability="provider:production", evidence_confidence=0.9, approved_classes=(ModelClass.FAST, ModelClass.GENERAL, ModelClass.DEEP))
    assert blocked.blocked is True and blocked.model_class is None
