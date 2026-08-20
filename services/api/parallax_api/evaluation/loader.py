from __future__ import annotations

import json
from pathlib import Path

from .schema import BenchmarkSuite, EvaluationArtifact, RecordedCandidate
from .security import assert_safe_payload


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_suite(path: str | Path) -> BenchmarkSuite:
    payload = _read_json(Path(path))
    assert_safe_payload(payload)
    return BenchmarkSuite.model_validate(payload)


def load_optimizer_suite(path: str | Path) -> BenchmarkSuite:
    """The only benchmark loader optimizer code should use."""

    suite = load_suite(path)
    if suite.purpose != "development":
        raise ValueError("optimizer-facing evaluation may load development suites only")
    return suite


def load_candidate(path: str | Path) -> RecordedCandidate:
    payload = _read_json(Path(path))
    assert_safe_payload(payload)
    return RecordedCandidate.model_validate(payload)


def load_evaluation_artifact(path: str | Path) -> EvaluationArtifact:
    payload = _read_json(Path(path))
    assert_safe_payload(payload)
    return EvaluationArtifact.model_validate(payload)
