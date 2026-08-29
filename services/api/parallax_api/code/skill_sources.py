from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Iterable

from .skill_intake import (
    CandidateKind,
    CandidateSourceAdapter,
    CandidateSourceObservation,
    CatalogEntry,
    SkillCatalog,
    SkillIntakePolicy,
    SourceTier,
    ingest_source,
)


_MAX_SOURCE_ID_BYTES = 64
_MAX_DISPLAY_NAME_BYTES = 96
_MAX_SOURCE_REF_BYTES = 224
_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9.-]{2,63}$")
_SOURCE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,223}$")


class SkillSourceFailureCode(StrEnum):
    INVALID_SOURCE_DEFINITION = "INVALID_SOURCE_DEFINITION"
    DUPLICATE_SOURCE = "DUPLICATE_SOURCE"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"
    SOURCE_IDENTITY_MISMATCH = "SOURCE_IDENTITY_MISMATCH"
    SOURCE_TIER_MISMATCH = "SOURCE_TIER_MISMATCH"
    CANDIDATE_KIND_NOT_ALLOWED = "CANDIDATE_KIND_NOT_ALLOWED"


class SkillSourceError(ValueError):
    def __init__(self, code: SkillSourceFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class SkillSourceDefinition:
    """Server-owned identity for a source that may supply bounded intake observations."""

    source_id: str
    display_name: str
    source_ref: str
    source_tier: SourceTier
    allowed_kinds: tuple[CandidateKind, ...]
    discovery_only: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_id, str)
            or len(self.source_id.encode("utf-8")) > _MAX_SOURCE_ID_BYTES
            or not _SOURCE_ID_RE.fullmatch(self.source_id)
        ):
            raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)
        if (
            not isinstance(self.display_name, str)
            or not self.display_name
            or self.display_name.strip() != self.display_name
            or len(self.display_name.encode("utf-8")) > _MAX_DISPLAY_NAME_BYTES
            or any(ord(char) < 32 or ord(char) == 127 for char in self.display_name)
        ):
            raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)
        if (
            not isinstance(self.source_ref, str)
            or len(self.source_ref.encode("utf-8")) > _MAX_SOURCE_REF_BYTES
            or not _SOURCE_REF_RE.fullmatch(self.source_ref)
        ):
            raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)
        if not isinstance(self.source_tier, SourceTier):
            try:
                object.__setattr__(self, "source_tier", SourceTier(self.source_tier))
            except (TypeError, ValueError) as exc:
                raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION) from exc
        kinds: list[CandidateKind] = []
        for value in self.allowed_kinds:
            try:
                kind = value if isinstance(value, CandidateKind) else CandidateKind(value)
            except (TypeError, ValueError) as exc:
                raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION) from exc
            kinds.append(kind)
        if not kinds or len(kinds) != len(set(kinds)):
            raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)
        object.__setattr__(self, "allowed_kinds", tuple(sorted(kinds, key=lambda item: item.value)))
        if not isinstance(self.discovery_only, bool):
            raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)

    def safe_metadata(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "display_name": self.display_name,
            "source_ref": self.source_ref,
            "source_tier": self.source_tier.value,
            "allowed_kinds": [kind.value for kind in self.allowed_kinds],
            "discovery_only": self.discovery_only,
            "grants_authority": False,
        }


class SkillSourceRegistry:
    """Server-owned source policy. Candidate content cannot assert a higher trust tier."""

    def __init__(self, definitions: Iterable[SkillSourceDefinition]) -> None:
        by_id: dict[str, SkillSourceDefinition] = {}
        by_ref: dict[str, SkillSourceDefinition] = {}
        for definition in definitions:
            if not isinstance(definition, SkillSourceDefinition):
                raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)
            if definition.source_id in by_id or definition.source_ref in by_ref:
                raise SkillSourceError(SkillSourceFailureCode.DUPLICATE_SOURCE)
            by_id[definition.source_id] = definition
            by_ref[definition.source_ref] = definition
        if not by_id:
            raise SkillSourceError(SkillSourceFailureCode.INVALID_SOURCE_DEFINITION)
        self._by_id = by_id
        self._by_ref = by_ref

    def source(self, source_id: str) -> SkillSourceDefinition:
        definition = self._by_id.get(source_id)
        if definition is None:
            raise SkillSourceError(SkillSourceFailureCode.UNKNOWN_SOURCE)
        return definition

    def sources(self) -> tuple[SkillSourceDefinition, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def safe_metadata(self) -> tuple[dict[str, object], ...]:
        return tuple(definition.safe_metadata() for definition in self.sources())

    def validate_observation(
        self,
        source_id: str,
        observation: CandidateSourceObservation,
    ) -> CandidateSourceObservation:
        definition = self.source(source_id)
        if not isinstance(observation, CandidateSourceObservation):
            raise SkillSourceError(SkillSourceFailureCode.SOURCE_IDENTITY_MISMATCH)
        if observation.source_ref != definition.source_ref:
            raise SkillSourceError(SkillSourceFailureCode.SOURCE_IDENTITY_MISMATCH)
        if observation.source_tier is not definition.source_tier:
            raise SkillSourceError(SkillSourceFailureCode.SOURCE_TIER_MISMATCH)
        if observation.kind not in definition.allowed_kinds:
            raise SkillSourceError(SkillSourceFailureCode.CANDIDATE_KIND_NOT_ALLOWED)
        return observation

    def ingest(
        self,
        source_id: str,
        adapter: CandidateSourceAdapter,
        *,
        policy: SkillIntakePolicy,
        catalog: SkillCatalog,
    ) -> tuple[CatalogEntry, ...]:
        registry = self

        class _ValidatedAdapter:
            def observations(self):
                for observation in adapter.observations():
                    yield registry.validate_observation(source_id, observation)

        return ingest_source(_ValidatedAdapter(), policy=policy, catalog=catalog)


OFFICIAL_AGENT_SKILLS = SkillSourceDefinition(
    source_id="agent-skills-official",
    display_name="Agent Skills official collection",
    source_ref="https://github.com/agentskills/skills",
    source_tier=SourceTier.OFFICIAL_ECOSYSTEM,
    allowed_kinds=(CandidateKind.SKILL,),
)

OFFICIAL_MCP_REGISTRY = SkillSourceDefinition(
    source_id="mcp-registry-official",
    display_name="MCP Registry official catalog",
    source_ref="https://registry.modelcontextprotocol.io",
    source_tier=SourceTier.OFFICIAL_ECOSYSTEM,
    allowed_kinds=(CandidateKind.TOOL,),
)


def default_public_skill_source_registry() -> SkillSourceRegistry:
    """Return the reviewed W9-S2 public discovery roots.

    These definitions authorize classification of bounded observations from the
    named sources only. They do not authorize network access, downloads,
    package installation, MCP startup, or tool execution.
    """

    return SkillSourceRegistry((OFFICIAL_AGENT_SKILLS, OFFICIAL_MCP_REGISTRY))
