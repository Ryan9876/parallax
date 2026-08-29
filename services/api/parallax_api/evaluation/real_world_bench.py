from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import UUID

from parallax_api.evaluation.parallax_bench import (
    BenchmarkCase,
    BenchmarkDimension,
    ParallaxBenchError,
    ProtectedCeiling,
)


REAL_WORLD_TEMPLATE_SCHEMA_VERSION = 1
_MAX_FIXTURE_BYTES = 64 * 1024
_MAX_REQUIREMENTS = 64
_MAX_ACCEPTANCE_CRITERIA = 128
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_REQUIREMENT_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,15}-[0-9]{2,3}$")
_ACCEPTANCE_ID_RE = re.compile(r"^AC-[0-9]{2,3}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RealWorldRequirement:
    requirement_id: str
    title: str
    outcome: str

    def __post_init__(self) -> None:
        if not isinstance(self.requirement_id, str) or _REQUIREMENT_ID_RE.fullmatch(self.requirement_id) is None:
            raise ParallaxBenchError("requirement_id must be a bounded canonical requirement token")
        object.__setattr__(self, "title", _bounded_text(self.title, "requirement title", 160))
        object.__setattr__(self, "outcome", _bounded_text(self.outcome, "requirement outcome", 1200))

    @property
    def digest(self) -> str:
        return _digest(
            {
                "requirement_id": self.requirement_id,
                "title": self.title,
                "outcome": self.outcome,
            }
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "requirement_id": self.requirement_id,
            "title": self.title,
            "outcome": self.outcome,
            "requirement_digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class RealWorldObjectiveTemplate:
    template_id: str
    template_version: str
    title: str
    objective: str
    objective_class: str
    repository_shape: str
    requirements: tuple[RealWorldRequirement, ...]
    comparable_dimensions: tuple[BenchmarkDimension, ...]
    expected_ceiling: ProtectedCeiling

    def __post_init__(self) -> None:
        object.__setattr__(self, "template_id", _token(self.template_id, "template_id"))
        object.__setattr__(self, "template_version", _version(self.template_version, "template_version"))
        object.__setattr__(self, "title", _bounded_text(self.title, "template title", 200))
        object.__setattr__(self, "objective", _bounded_text(self.objective, "template objective", 1600))
        object.__setattr__(self, "objective_class", _token(self.objective_class, "objective_class"))
        object.__setattr__(self, "repository_shape", _token(self.repository_shape, "repository_shape"))

        requirements = tuple(self.requirements)
        if not requirements or len(requirements) > _MAX_REQUIREMENTS:
            raise ParallaxBenchError("real-world requirements must be bounded and non-empty")
        if any(not isinstance(item, RealWorldRequirement) for item in requirements):
            raise ParallaxBenchError("real-world requirements must be canonical RealWorldRequirement values")
        requirement_ids = tuple(item.requirement_id for item in requirements)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ParallaxBenchError("real-world requirement IDs must be unique")
        object.__setattr__(self, "requirements", requirements)

        try:
            dimensions = tuple(
                item if isinstance(item, BenchmarkDimension) else BenchmarkDimension(item)
                for item in self.comparable_dimensions
            )
        except (TypeError, ValueError) as exc:
            raise ParallaxBenchError("invalid real-world comparable dimension") from exc
        if not dimensions or len(dimensions) != len(set(dimensions)):
            raise ParallaxBenchError("real-world comparable dimensions must be unique and non-empty")
        object.__setattr__(self, "comparable_dimensions", tuple(sorted(dimensions, key=lambda item: item.value)))

        try:
            ceiling = self.expected_ceiling if isinstance(self.expected_ceiling, ProtectedCeiling) else ProtectedCeiling(self.expected_ceiling)
        except (TypeError, ValueError) as exc:
            raise ParallaxBenchError("invalid real-world expected ceiling") from exc
        object.__setattr__(self, "expected_ceiling", ceiling)

    @property
    def fixture_digest(self) -> str:
        return _digest(self.as_dict(include_fixture_digest=False))

    def as_dict(self, *, include_fixture_digest: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "template_id": self.template_id,
            "template_version": self.template_version,
            "title": self.title,
            "objective": self.objective,
            "objective_class": self.objective_class,
            "repository_shape": self.repository_shape,
            "requirements": [item.as_dict() for item in self.requirements],
            "comparable_dimensions": [item.value for item in self.comparable_dimensions],
            "expected_ceiling": self.expected_ceiling.value,
        }
        if include_fixture_digest:
            payload["fixture_digest"] = self.fixture_digest
        return payload


@dataclass(frozen=True, slots=True)
class CanonicalAcceptanceCriterion:
    acceptance_id: str
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.acceptance_id, str) or _ACCEPTANCE_ID_RE.fullmatch(self.acceptance_id) is None:
            raise ParallaxBenchError("acceptance_id must be canonical AC-NN text")
        object.__setattr__(self, "text", _bounded_text(self.text, "acceptance criterion text", 6000))

    def as_dict(self) -> dict[str, str]:
        return {"acceptance_id": self.acceptance_id, "text": self.text}


@dataclass(frozen=True, slots=True)
class CanonicalWorkSpecificationEvidence:
    project_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    work_specification_status: str
    acceptance_criteria: tuple[CanonicalAcceptanceCriterion, ...]
    repository_shape: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, "work_specification_id"))
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise ParallaxBenchError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha(self.work_specification_digest, "work_specification_digest"),
        )
        if self.work_specification_status != "APPROVED":
            raise ParallaxBenchError("real-world binding requires an APPROVED Work Specification")

        criteria = tuple(self.acceptance_criteria)
        if not criteria or len(criteria) > _MAX_ACCEPTANCE_CRITERIA:
            raise ParallaxBenchError("canonical acceptance criteria must be bounded and non-empty")
        if any(not isinstance(item, CanonicalAcceptanceCriterion) for item in criteria):
            raise ParallaxBenchError("canonical acceptance criteria contain a non-canonical value")
        acceptance_ids = tuple(item.acceptance_id for item in criteria)
        if len(acceptance_ids) != len(set(acceptance_ids)):
            raise ParallaxBenchError("canonical acceptance IDs must be unique")
        object.__setattr__(self, "acceptance_criteria", criteria)
        object.__setattr__(self, "repository_shape", _token(self.repository_shape, "repository_shape"))

    @property
    def acceptance_ids(self) -> tuple[str, ...]:
        return tuple(item.acceptance_id for item in self.acceptance_criteria)

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "work_specification_status": self.work_specification_status,
            "acceptance_criteria": [item.as_dict() for item in self.acceptance_criteria],
            "repository_shape": self.repository_shape,
        }


def validate_real_world_template_catalog(
    templates: Iterable[RealWorldObjectiveTemplate],
) -> tuple[RealWorldObjectiveTemplate, ...]:
    materialized = tuple(templates)
    if not materialized:
        raise ParallaxBenchError("real-world template catalog must be non-empty")
    if any(not isinstance(item, RealWorldObjectiveTemplate) for item in materialized):
        raise ParallaxBenchError("real-world template catalog contains a non-canonical template")

    seen: dict[tuple[str, str], str] = {}
    for template in materialized:
        identity = (template.template_id, template.template_version)
        existing = seen.get(identity)
        if existing is not None:
            if existing != template.fixture_digest:
                raise ParallaxBenchError("real-world template identity conflicts with different content")
            raise ParallaxBenchError("real-world template identity must be unique")
        seen[identity] = template.fixture_digest
    return tuple(sorted(materialized, key=lambda item: (item.template_id, item.template_version)))


def bind_real_world_template(
    template: RealWorldObjectiveTemplate,
    evidence: CanonicalWorkSpecificationEvidence,
) -> BenchmarkCase:
    """Bind frozen evaluation requirements to ordinary canonical Project/spec evidence.

    Admission is deliberately deterministic. The binder never asks a model to infer
    semantic equivalence or to repair missing benchmark requirement tokens.
    """

    if not isinstance(template, RealWorldObjectiveTemplate):
        raise ParallaxBenchError("template must be a canonical RealWorldObjectiveTemplate")
    if not isinstance(evidence, CanonicalWorkSpecificationEvidence):
        raise ParallaxBenchError("evidence must be canonical Work Specification evidence")
    if evidence.repository_shape != template.repository_shape:
        raise ParallaxBenchError("canonical repository shape does not match real-world template")

    for requirement in template.requirements:
        count = sum(_requirement_occurrences(criterion.text, requirement.requirement_id) for criterion in evidence.acceptance_criteria)
        if count != 1:
            raise ParallaxBenchError(
                f"benchmark requirement {requirement.requirement_id} must appear exactly once across canonical acceptance text; observed {count}"
            )

    return BenchmarkCase(
        case_id=template.template_id,
        case_version=template.template_version,
        objective_class=template.objective_class,
        project_id=evidence.project_id,
        work_specification_id=evidence.work_specification_id,
        work_specification_revision=evidence.work_specification_revision,
        work_specification_digest=evidence.work_specification_digest,
        acceptance_ids=evidence.acceptance_ids,
        repository_shape=evidence.repository_shape,
        comparable_dimensions=template.comparable_dimensions,
        expected_ceiling=template.expected_ceiling,
        fixture_digest=template.fixture_digest,
    )


def load_real_world_template(path: str | Path) -> RealWorldObjectiveTemplate:
    fixture_path = Path(path)
    try:
        size = fixture_path.stat().st_size
    except OSError as exc:
        raise ParallaxBenchError("real-world fixture cannot be read") from exc
    if size <= 0 or size > _MAX_FIXTURE_BYTES:
        raise ParallaxBenchError("real-world fixture size is invalid")

    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParallaxBenchError("real-world fixture must be valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ParallaxBenchError("real-world fixture must be a JSON object")

    expected_keys = {
        "schema_version",
        "template_id",
        "template_version",
        "title",
        "objective",
        "objective_class",
        "repository_shape",
        "requirements",
        "comparable_dimensions",
        "expected_ceiling",
        "fixture_digest",
    }
    if set(payload) != expected_keys:
        raise ParallaxBenchError("real-world fixture contains unexpected or missing fields")
    if payload.get("schema_version") != REAL_WORLD_TEMPLATE_SCHEMA_VERSION:
        raise ParallaxBenchError("unsupported real-world template schema version")

    raw_requirements = payload.get("requirements")
    if not isinstance(raw_requirements, list):
        raise ParallaxBenchError("real-world fixture requirements must be a list")
    requirements: list[RealWorldRequirement] = []
    for raw in raw_requirements:
        if not isinstance(raw, dict) or set(raw) != {"requirement_id", "title", "outcome", "requirement_digest"}:
            raise ParallaxBenchError("real-world fixture requirement shape is invalid")
        requirement = RealWorldRequirement(
            requirement_id=raw.get("requirement_id"),
            title=raw.get("title"),
            outcome=raw.get("outcome"),
        )
        if raw.get("requirement_digest") != requirement.digest:
            raise ParallaxBenchError(f"real-world requirement {requirement.requirement_id} digest mismatch")
        requirements.append(requirement)

    dimensions = payload.get("comparable_dimensions")
    if not isinstance(dimensions, list):
        raise ParallaxBenchError("real-world comparable_dimensions must be a list")

    template = RealWorldObjectiveTemplate(
        template_id=payload.get("template_id"),
        template_version=payload.get("template_version"),
        title=payload.get("title"),
        objective=payload.get("objective"),
        objective_class=payload.get("objective_class"),
        repository_shape=payload.get("repository_shape"),
        requirements=tuple(requirements),
        comparable_dimensions=tuple(dimensions),
        expected_ceiling=payload.get("expected_ceiling"),
    )
    declared_digest = payload.get("fixture_digest")
    if not isinstance(declared_digest, str) or _SHA_RE.fullmatch(declared_digest) is None:
        raise ParallaxBenchError("real-world fixture_digest must be lowercase sha256 hex")
    if declared_digest != template.fixture_digest:
        raise ParallaxBenchError("real-world fixture digest mismatch")
    return template


def safe_real_world_template_json(template: RealWorldObjectiveTemplate) -> str:
    if not isinstance(template, RealWorldObjectiveTemplate):
        raise ParallaxBenchError("template must be a canonical RealWorldObjectiveTemplate")
    payload = {"schema_version": REAL_WORLD_TEMPLATE_SCHEMA_VERSION, **template.as_dict()}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _requirement_occurrences(text: str, requirement_id: str) -> int:
    pattern = re.compile(rf"(?<![A-Z0-9-]){re.escape(requirement_id)}(?![A-Z0-9-])")
    return len(pattern.findall(text))


def _bounded_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ParallaxBenchError(f"{field} must be text")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum or "\x00" in normalized:
        raise ParallaxBenchError(f"{field} must be bounded non-empty text")
    return normalized


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ParallaxBenchError(f"{field} must be UUID text")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as exc:
        raise ParallaxBenchError(f"{field} must be UUID text") from exc
    return str(parsed)


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ParallaxBenchError(f"{field} must be lowercase sha256 hex")
    return value


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None:
        raise ParallaxBenchError(f"{field} must be a bounded token")
    return value


def _version(value: str, field: str) -> str:
    if not isinstance(value, str) or _VERSION_RE.fullmatch(value) is None:
        raise ParallaxBenchError(f"{field} must be a bounded version")
    return value


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()
