from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from parallax_api.evaluation.app_builder import AppBuilderRecordedEvidence


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "benchmarks" / "parallax-app-builder" / "fixtures" / "development-good-v0.1.json"


def test_recorded_observations_are_individually_bounded():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cases"][0]["observations"] = ["x" * 241]

    with pytest.raises(ValidationError, match="at most 240 characters"):
        AppBuilderRecordedEvidence.model_validate(payload)
