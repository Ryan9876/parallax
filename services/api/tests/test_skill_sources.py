from __future__ import annotations

from hashlib import sha256
import json

import pytest

from parallax_api.code.skill_intake import (
    CandidateKind,
    CandidateSourceObservation,
    IntakeDisposition,
    SkillCatalog,
    SkillIntakePolicy,
    SourceTier,
)
from parallax_api.code.skill_sources import (
    OFFICIAL_AGENT_SKILLS,
    OFFICIAL_MCP_REGISTRY,
    SkillSourceDefinition,
    SkillSourceError,
    SkillSourceFailureCode,
    SkillSourceRegistry,
    default_public_skill_source_registry,
)


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def skill_observation(
    *,
    source_ref: str = OFFICIAL_AGENT_SKILLS.source_ref,
    source_tier: SourceTier = SourceTier.OFFICIAL_ECOSYSTEM,
    kind: CandidateKind = CandidateKind.SKILL,
) -> CandidateSourceObservation:
    return CandidateSourceObservation(
        kind=kind,
        source_tier=source_tier,
        source_ref=source_ref,
        upstream_name="responsive-ui-audit",
        upstream_ref="commit:abc123",
        content_digest=digest("bounded skill source body"),
        license_id="Apache-2.0",
        objective_hints=("implement-feature",),
        capability_hints=("code.write",),
        compatibility_hints=("react",),
        inspection_text="Inspect responsive behavior and produce bounded evidence.",
    )


def tool_observation() -> CandidateSourceObservation:
    return CandidateSourceObservation(
        kind=CandidateKind.TOOL,
        source_tier=SourceTier.OFFICIAL_ECOSYSTEM,
        source_ref=OFFICIAL_MCP_REGISTRY.source_ref,
        upstream_name="io.example/read-only-tool",
        upstream_ref="1.0.0",
        content_digest=digest("bounded registry metadata"),
        license_id="MIT",
        capability_hints=("tool.read",),
        inspection_text="Read-only metadata for a tool candidate.",
    )


def test_default_registry_contains_reviewed_official_roots_without_authority() -> None:
    registry = default_public_skill_source_registry()
    metadata = registry.safe_metadata()

    assert [item["source_id"] for item in metadata] == [
        "agent-skills-official",
        "mcp-registry-official",
    ]
    serialized = json.dumps(metadata, sort_keys=True)
    assert "https://github.com/agentskills/skills" in serialized
    assert "https://registry.modelcontextprotocol.io" in serialized
    assert all(item["grants_authority"] is False for item in metadata)


def test_source_registry_rejects_candidate_self_asserted_official_tier() -> None:
    registry = default_public_skill_source_registry()
    spoofed = skill_observation(source_ref="https://github.com/untrusted/community-skills")

    with pytest.raises(SkillSourceError) as error:
        registry.validate_observation("agent-skills-official", spoofed)
    assert error.value.code is SkillSourceFailureCode.SOURCE_IDENTITY_MISMATCH


def test_source_registry_rejects_tier_drift_even_for_known_source_ref() -> None:
    registry = default_public_skill_source_registry()
    downgraded_or_caller_supplied = skill_observation(source_tier=SourceTier.CURATED_DISCOVERY)

    with pytest.raises(SkillSourceError) as error:
        registry.validate_observation("agent-skills-official", downgraded_or_caller_supplied)
    assert error.value.code is SkillSourceFailureCode.SOURCE_TIER_MISMATCH


def test_source_registry_enforces_skill_vs_tool_source_kind() -> None:
    registry = default_public_skill_source_registry()

    with pytest.raises(SkillSourceError) as skill_source_error:
        registry.validate_observation(
            "agent-skills-official",
            skill_observation(kind=CandidateKind.TOOL),
        )
    assert skill_source_error.value.code is SkillSourceFailureCode.CANDIDATE_KIND_NOT_ALLOWED

    with pytest.raises(SkillSourceError) as tool_source_error:
        registry.validate_observation("mcp-registry-official", skill_observation())
    assert tool_source_error.value.code is SkillSourceFailureCode.SOURCE_IDENTITY_MISMATCH


def test_registered_source_ingestion_still_quarantines_and_never_auto_admits() -> None:
    class AgentSkillsAdapter:
        def observations(self):
            yield skill_observation()

    catalog = SkillCatalog()
    entries = default_public_skill_source_registry().ingest(
        "agent-skills-official",
        AgentSkillsAdapter(),
        policy=SkillIntakePolicy(),
        catalog=catalog,
    )

    assert len(entries) == 1
    assert entries[0].disposition is IntakeDisposition.QUARANTINED
    assert entries[0].candidate.kind is CandidateKind.SKILL
    assert entries[0].candidate.source_tier is SourceTier.OFFICIAL_ECOSYSTEM
    assert entries[0].candidate.safe_metadata()["grants_authority"] is False


def test_registered_mcp_source_ingestion_produces_tool_metadata_only() -> None:
    class McpAdapter:
        def observations(self):
            yield tool_observation()

    entries = default_public_skill_source_registry().ingest(
        "mcp-registry-official",
        McpAdapter(),
        policy=SkillIntakePolicy(),
        catalog=SkillCatalog(),
    )

    assert len(entries) == 1
    assert entries[0].candidate.kind is CandidateKind.TOOL
    assert entries[0].disposition is IntakeDisposition.QUARANTINED
    assert entries[0].safe_metadata()["grants_authority"] is False


def test_registry_rejects_duplicate_source_ids_or_refs() -> None:
    same_ref = SkillSourceDefinition(
        source_id="another-source",
        display_name="Another source",
        source_ref=OFFICIAL_AGENT_SKILLS.source_ref,
        source_tier=SourceTier.VENDOR_NATIVE,
        allowed_kinds=(CandidateKind.SKILL,),
    )
    with pytest.raises(SkillSourceError) as error:
        SkillSourceRegistry((OFFICIAL_AGENT_SKILLS, same_ref))
    assert error.value.code is SkillSourceFailureCode.DUPLICATE_SOURCE


def test_unknown_source_id_fails_closed() -> None:
    with pytest.raises(SkillSourceError) as error:
        default_public_skill_source_registry().validate_observation(
            "not-registered",
            skill_observation(),
        )
    assert error.value.code is SkillSourceFailureCode.UNKNOWN_SOURCE
