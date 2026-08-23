from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from hashlib import sha256
import json

from .optimization_contracts import (MAX_REFS, MAX_REGISTRY_RECORDS, OptimizationPolicyError, ValidationBoundary, _canonical_digest, _digest, _refs, _repo_path, _safe_token)

@dataclass(frozen=True, slots=True)
class ImpactRule:
    pattern: str
    components: tuple[str, ...]
    contracts: tuple[str, ...]
    platforms: tuple[str, ...]
    checks: tuple[str, ...]
    proven: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern", _repo_path(self.pattern, field="impact_pattern"))
        object.__setattr__(self, "components", _refs(self.components, field="component"))
        object.__setattr__(self, "contracts", _refs(self.contracts, field="contract"))
        object.__setattr__(self, "platforms", _refs(self.platforms, field="platform"))
        object.__setattr__(self, "checks", _refs(self.checks, field="check"))
        if not self.checks:
            raise OptimizationPolicyError("impact rule must name at least one validation check")

    def to_record(self) -> dict[str, object]:
        return {
            "pattern": self.pattern,
            "components": list(self.components),
            "contracts": list(self.contracts),
            "platforms": list(self.platforms),
            "checks": list(self.checks),
            "proven": self.proven,
        }


@dataclass(frozen=True, slots=True)
class ValidationSelection:
    changed_paths: tuple[str, ...]
    graph_digest: str
    selected_checks: tuple[str, ...]
    excluded_checks: tuple[str, ...]
    excluded_evidence: tuple[str, ...]
    impacted_components: tuple[str, ...]
    impacted_contracts: tuple[str, ...]
    impacted_platforms: tuple[str, ...]
    conservative: bool
    confidence: str


@dataclass(frozen=True, slots=True)
class ChangeImpactGraph:
    version: str
    rules: tuple[ImpactRule, ...]
    global_invariants: tuple[str, ...]
    full_suite_checks: tuple[str, ...]
    configuration_paths: tuple[str, ...] = (".parallax/change-impact.json",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "version", _safe_token(self.version, field="impact_version"))
        if not self.rules or len(self.rules) > MAX_REGISTRY_RECORDS:
            raise OptimizationPolicyError("impact graph must contain bounded rules")
        object.__setattr__(self, "global_invariants", _refs(self.global_invariants, field="global_invariant"))
        object.__setattr__(self, "full_suite_checks", _refs(self.full_suite_checks, field="full_suite_check", limit=MAX_REGISTRY_RECORDS))
        object.__setattr__(self, "configuration_paths", tuple(_repo_path(path) for path in self.configuration_paths))
        if not set(self.global_invariants).issubset(set(self.full_suite_checks)):
            raise OptimizationPolicyError("global invariants must be part of the full protected suite")

    def to_record(self) -> dict[str, object]:
        return {
            "version": self.version,
            "rules": [rule.to_record() for rule in sorted(self.rules, key=lambda item: item.pattern)],
            "global_invariants": sorted(self.global_invariants),
            "full_suite_checks": sorted(self.full_suite_checks),
            "configuration_paths": sorted(self.configuration_paths),
        }

    @property
    def digest(self) -> str:
        return _canonical_digest(self.to_record())

    def select(self, changed_paths: tuple[str, ...], *, boundary: ValidationBoundary) -> ValidationSelection:
        paths = tuple(_repo_path(value) for value in changed_paths)
        if not paths or len(paths) > MAX_REFS:
            raise OptimizationPolicyError("validation selection requires bounded changed paths")
        if len(set(paths)) != len(paths):
            raise OptimizationPolicyError("changed paths must be unique")
        force_full = boundary is not ValidationBoundary.DEVELOPMENT_FAST or any(path in self.configuration_paths for path in paths)
        selected = set(self.global_invariants)
        components: set[str] = set()
        contracts: set[str] = set()
        platforms: set[str] = set()
        unknown = False
        conflict = False

        by_pattern: dict[str, set[str]] = {}
        for rule in self.rules:
            signature = json.dumps(rule.to_record(), sort_keys=True, separators=(",", ":"))
            by_pattern.setdefault(rule.pattern, set()).add(signature)
        conflicting_patterns = {pattern for pattern, signatures in by_pattern.items() if len(signatures) > 1}

        for path in paths:
            matches = [rule for rule in self.rules if fnmatchcase(path, rule.pattern)]
            if not matches:
                unknown = True
                continue
            for rule in matches:
                if not rule.proven or rule.pattern in conflicting_patterns:
                    conflict = True
                selected.update(rule.checks)
                components.update(rule.components)
                contracts.update(rule.contracts)
                platforms.update(rule.platforms)

        conservative = force_full or unknown or conflict
        if conservative:
            selected = set(self.full_suite_checks)
        else:
            selected.update(self.global_invariants)
        full = set(self.full_suite_checks)
        excluded = tuple(sorted(full - selected))
        evidence = tuple(f"impact:{self.digest}:{sha256(check.encode('utf-8')).hexdigest()[:16]}" for check in excluded)
        return ValidationSelection(
            changed_paths=paths,
            graph_digest=self.digest,
            selected_checks=tuple(sorted(selected)),
            excluded_checks=excluded,
            excluded_evidence=evidence,
            impacted_components=tuple(sorted(components)),
            impacted_contracts=tuple(sorted(contracts)),
            impacted_platforms=tuple(sorted(platforms)),
            conservative=conservative,
            confidence="CONSERVATIVE_FULL" if conservative else "PROVEN_IMPACT",
        )


@dataclass(frozen=True, slots=True)
class WarmEnvironmentIdentity:
    runtime: str
    operating_system: str
    architecture: str
    toolchain_digest: str
    dependency_digest: str
    configuration_digest: str
    source_digest: str
    cache_schema_version: str
    digest: str

    @classmethod
    def build(
        cls,
        *,
        runtime: str,
        operating_system: str,
        architecture: str,
        toolchain_digest: str,
        dependency_digest: str,
        configuration_digest: str,
        source_digest: str,
        cache_schema_version: str,
    ) -> "WarmEnvironmentIdentity":
        payload = {
            "runtime": _safe_token(runtime, field="runtime"),
            "operating_system": _safe_token(operating_system, field="operating_system"),
            "architecture": _safe_token(architecture, field="architecture"),
            "toolchain_digest": _digest(toolchain_digest, field="toolchain_digest"),
            "dependency_digest": _digest(dependency_digest, field="dependency_digest"),
            "configuration_digest": _digest(configuration_digest, field="configuration_digest"),
            "source_digest": _digest(source_digest, field="source_digest"),
            "cache_schema_version": _safe_token(cache_schema_version, field="cache_schema_version"),
        }
        return cls(**payload, digest=_canonical_digest(payload))


@dataclass(frozen=True, slots=True)
class WarmCacheRecord:
    identity_digest: str
    provenance_complete: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _digest(self.identity_digest, field="identity_digest")
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="cache_evidence"))
        if not self.evidence_refs:
            raise OptimizationPolicyError("cache record requires provenance evidence")

    def eligible_for(self, expected: WarmEnvironmentIdentity) -> bool:
        return self.provenance_complete and self.identity_digest == expected.digest
