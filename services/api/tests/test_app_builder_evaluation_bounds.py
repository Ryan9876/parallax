from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from parallax_api.evaluation.app_builder import AppBuilderBenchmarkCase, AppBuilderRecordedEvidence


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "benchmarks" / "parallax-app-builder" / "fixtures" / "development-good-v0.1.json"


def test_recorded_observations_are_individually_bounded():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cases"][0]["observations"] = ["x" * 241]

    with pytest.raises(ValidationError, match="at most 240 characters"):
        AppBuilderRecordedEvidence.model_validate(payload)


def _case_payload(requirements: list[dict[str, object]]) -> dict[str, object]:
    return {
        "case_id": "malformed-case",
        "category": "project_isolation",
        "objective": "Reject internally malformed observation requirements.",
        "requirements": requirements,
        "minimum_score": 1.0,
    }


def test_case_rejects_required_forbidden_observation_contradiction():
    payload = _case_payload(
        [
            {"requirement_id": "must-deny", "kind": "required", "observation": "tool.decision=deny"},
            {"requirement_id": "must-not-deny", "kind": "forbidden", "observation": " TOOL.DECISION=DENY "},
        ]
    )

    with pytest.raises(ValidationError, match="duplicate or contradict"):
        AppBuilderBenchmarkCase.model_validate(payload)


def test_case_rejects_whitespace_only_requirement():
    payload = _case_payload(
        [{"requirement_id": "blank", "kind": "required", "observation": "   "}]
    )

    with pytest.raises(ValidationError, match="empty or whitespace-only"):
        AppBuilderBenchmarkCase.model_validate(payload)
