from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class OfflineSpecCompilation:
    plan: Mapping[str, tuple[str, ...]]
    critique: tuple[str, ...]
    program_version: str = "offline-spec-compiler-v1"


def _criterion_line(item: Mapping[str, str], action: str) -> str:
    return f"{item['id']}: {action} — {item['protected_requirement']}"


def compile_spec_offline(
    specification: str,
    acceptance_contract: Sequence[Mapping[str, str]],
) -> OfflineSpecCompilation:
    """Deterministic provider-independent development compiler.

    This is deliberately not DSPy evidence and is never accepted by the
    --require-dspy release gate. It exists so compiler shape, protected
    acceptance injection, serialization and regression behavior can run without
    network/provider/model availability.
    """

    if not isinstance(specification, str) or not specification.strip():
        raise ValueError("offline specification must be non-empty")
    criteria = tuple(acceptance_contract)
    if not criteria:
        raise ValueError("offline acceptance contract must be non-empty")

    spec_digest = sha256(specification.encode("utf-8")).hexdigest()[:12]
    architecture = tuple(
        _criterion_line(item, "preserve architecture boundary")
        for item in criteria[:3]
    )
    work_items = tuple(
        _criterion_line(item, "implement bounded work")
        for item in criteria[3:7]
    )
    validations = tuple(
        _criterion_line(item, "validate protected requirement")
        for item in criteria[:3]
    )
    risks = (
        f"offline:{spec_digest}: development output must never satisfy authentic DSPy release evidence",
        "cache/optimization changes must remain outside lifecycle, lineage, lease and promotion authority",
    )
    return OfflineSpecCompilation(
        plan={
            "architecture_decisions": architecture,
            "work_items": work_items,
            "validations": validations,
            "risks": risks,
        },
        critique=(
            "Offline deterministic compiler exercised contract shape only; provider-backed plan quality is not implied.",
        ),
    )


def canonical_offline_digest(result: OfflineSpecCompilation) -> str:
    payload = {
        "plan": {key: list(value) for key, value in result.plan.items()},
        "critique": list(result.critique),
        "program_version": result.program_version,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
