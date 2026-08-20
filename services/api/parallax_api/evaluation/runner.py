from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .protected_scoring import EVALUATOR_VERSION, evaluate_case
from .schema import BenchmarkSuite, CategoryEvaluation, EvaluationArtifact, RecordedCandidate
from .security import assert_safe_payload


def canonical_digest(payload: object) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def evaluate_recorded_candidate(suite: BenchmarkSuite, candidate: RecordedCandidate) -> EvaluationArtifact:
    if candidate.suite_id != suite.suite_id or candidate.suite_version != suite.suite_version:
        raise ValueError("candidate suite identity does not match benchmark suite")

    case_ids = {case.case_id for case in suite.cases}
    extra_outputs = sorted(set(candidate.outputs) - case_ids)
    if extra_outputs:
        raise ValueError(f"candidate contains outputs for unknown cases: {extra_outputs}")

    assert_safe_payload(candidate)

    results = [evaluate_case(case, candidate.outputs.get(case.case_id, "")) for case in suite.cases]
    case_by_id = {case.case_id: case for case in suite.cases}

    category_results: list[CategoryEvaluation] = []
    for category, minimum in sorted(suite.category_minimums.items()):
        members = [result for result in results if result.category == category]
        total_weight = sum(case_by_id[result.case_id].case_weight for result in members)
        score = sum(result.score * case_by_id[result.case_id].case_weight for result in members) / total_weight
        category_results.append(
            CategoryEvaluation(
                category=category,
                score=score,
                minimum_score=minimum,
                passed=score >= minimum and all(result.passed for result in members),
            )
        )

    total_weight = sum(case.case_weight for case in suite.cases)
    aggregate = sum(result.score * case_by_id[result.case_id].case_weight for result in results) / total_weight
    protected_pass = (
        aggregate >= suite.minimum_aggregate_score
        and all(result.passed for result in results)
        and all(category.passed for category in category_results)
    )

    artifact = EvaluationArtifact(
        run_id=f"eval-{uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        spec_id=suite.spec_id,
        suite_id=suite.suite_id,
        suite_version=suite.suite_version,
        suite_purpose=suite.purpose,
        evaluator_version=EVALUATOR_VERSION,
        candidate_artifact_id=candidate.artifact_id,
        candidate_program_version=candidate.program_version,
        candidate_model_id=candidate.model_id,
        input_artifact_digest=canonical_digest(candidate),
        case_results=results,
        category_results=category_results,
        aggregate_score=aggregate,
        minimum_aggregate_score=suite.minimum_aggregate_score,
        protected_pass=protected_pass,
    )
    assert_safe_payload(artifact)
    return artifact


def write_evaluation_artifact(artifact: EvaluationArtifact, evidence_dir: str | Path) -> Path:
    assert_safe_payload(artifact)
    root = Path(evidence_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / f"{artifact.run_id}.json").resolve()
    if target.parent != root:
        raise ValueError("evaluation evidence path escaped configured evidence directory")
    target.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target
