from __future__ import annotations

import hashlib
import json

from ..models import WorkSpecification


def _items(payload: str) -> list[str]:
    value = json.loads(payload)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("work specification contains an invalid bounded list")
    return value


def work_specification_contract(specification: WorkSpecification) -> dict[str, object]:
    return {
        "id": specification.id,
        "revision": specification.revision,
        "title": specification.title,
        "objective": specification.objective,
        "constraints": _items(specification.constraints_json),
        "acceptance_criteria": _items(specification.acceptance_criteria_json),
        "risks": _items(specification.risks_json),
        "open_questions": _items(specification.open_questions_json),
    }


def work_specification_digest(specification: WorkSpecification) -> str:
    encoded = json.dumps(
        work_specification_contract(specification),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def acceptance_map(specification: WorkSpecification) -> list[dict[str, str]]:
    criteria = _items(specification.acceptance_criteria_json)
    return [
        {"id": f"AC-{index:02d}", "text": text}
        for index, text in enumerate(criteria, start=1)
    ]


def required_acceptance_ids(specification: WorkSpecification) -> set[str]:
    return {item["id"] for item in acceptance_map(specification)}
