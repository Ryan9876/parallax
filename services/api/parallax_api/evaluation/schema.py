from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SuitePurpose = Literal["development", "promotion"]
AssertionKind = Literal["contains", "not_contains", "exact"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProtectedAssertion(StrictModel):
    assertion_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    kind: AssertionKind
    value: str = Field(min_length=1, max_length=1000)
    critical: bool = True


class ScoringWeights(StrictModel):
    required_coverage: float = Field(ge=0.0, le=1.0)
    forbidden: float = Field(ge=0.0, le=1.0)
    assertions: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def sum_to_one(self) -> "ScoringWeights":
        total = self.required_coverage + self.forbidden + self.assertions
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"scoring weights must sum to 1.0, got {total:.6f}")
        return self


class BenchmarkCase(StrictModel):
    case_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    category: str = Field(min_length=1, max_length=80)
    objective: str = Field(min_length=1, max_length=4000)
    context: str = Field(default="", max_length=8000)
    required_terms: list[str] = Field(default_factory=list, max_length=32)
    forbidden_terms: list[str] = Field(default_factory=list, max_length=32)
    protected_assertions: list[ProtectedAssertion] = Field(default_factory=list, max_length=32)
    weights: ScoringWeights
    minimum_score: float = Field(ge=0.0, le=1.0)
    case_weight: float = Field(default=1.0, gt=0.0, le=100.0)
    max_output_chars: int | None = Field(default=None, ge=24, le=100_000)

    @model_validator(mode="after")
    def validate_contract(self) -> "BenchmarkCase":
        if not (self.required_terms or self.forbidden_terms or self.protected_assertions):
            raise ValueError("benchmark case has no executable protected contract")

        for label, values in (
            ("required_terms", self.required_terms),
            ("forbidden_terms", self.forbidden_terms),
        ):
            normalized = [value.strip().casefold() for value in values]
            if any(not value for value in normalized):
                raise ValueError(f"{label} may not contain empty values")
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{label} contains duplicates")

        assertion_ids = [item.assertion_id for item in self.protected_assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("protected assertion IDs must be unique within a case")

        if not self.required_terms and self.weights.required_coverage != 0.0:
            raise ValueError("required_coverage weight must be zero when required_terms is empty")
        if not self.forbidden_terms and self.weights.forbidden != 0.0:
            raise ValueError("forbidden weight must be zero when forbidden_terms is empty")
        if not self.protected_assertions and self.weights.assertions != 0.0:
            raise ValueError("assertions weight must be zero when protected_assertions is empty")
        return self


class BenchmarkSuite(StrictModel):
    schema_version: Literal["1"]
    suite_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    suite_version: str = Field(pattern=r"^v\d+\.\d+$")
    spec_id: str = Field(pattern=r"^P2-V\d+\.\d+\.\d+$")
    purpose: SuitePurpose
    minimum_aggregate_score: float = Field(ge=0.0, le=1.0)
    category_minimums: dict[str, float]
    cases: list[BenchmarkCase] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_suite(self) -> "BenchmarkSuite":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark suite contains duplicate case IDs")

        categories = {case.category for case in self.cases}
        if set(self.category_minimums) != categories:
            missing = sorted(categories - set(self.category_minimums))
            extra = sorted(set(self.category_minimums) - categories)
            raise ValueError(f"category floors must exactly match suite categories; missing={missing}, extra={extra}")
        for category, threshold in self.category_minimums.items():
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"category threshold out of range: {category}")
        return self


class RecordedCandidate(StrictModel):
    artifact_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    suite_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    suite_version: str = Field(pattern=r"^v\d+\.\d+$")
    program_version: str = Field(min_length=1, max_length=200)
    model_id: str | None = Field(default=None, max_length=300)
    outputs: dict[str, str]


class CaseEvaluation(StrictModel):
    case_id: str
    category: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    critical_failure: bool
    failures: list[str]
    required_coverage: float = Field(ge=0.0, le=1.0)
    forbidden_score: float = Field(ge=0.0, le=1.0)
    assertion_score: float = Field(ge=0.0, le=1.0)
    output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class CategoryEvaluation(StrictModel):
    category: str
    score: float = Field(ge=0.0, le=1.0)
    minimum_score: float = Field(ge=0.0, le=1.0)
    passed: bool


class EvaluationArtifact(StrictModel):
    artifact_version: Literal["1"] = "1"
    run_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    timestamp: datetime
    spec_id: str
    suite_id: str
    suite_version: str
    suite_purpose: SuitePurpose
    evaluator_version: str
    candidate_artifact_id: str
    candidate_program_version: str
    candidate_model_id: str | None = None
    input_artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    case_results: list[CaseEvaluation]
    category_results: list[CategoryEvaluation]
    aggregate_score: float = Field(ge=0.0, le=1.0)
    minimum_aggregate_score: float = Field(ge=0.0, le=1.0)
    protected_pass: bool
    no_chain_of_thought: Literal[True] = True


class PromotionDecision(StrictModel):
    decision_version: Literal["1"] = "1"
    policy_version: str
    baseline_run_id: str
    challenger_run_id: str
    passed: bool
    reasons: list[str]
    aggregate_delta: float
    category_deltas: dict[str, float]
    no_chain_of_thought: Literal[True] = True
