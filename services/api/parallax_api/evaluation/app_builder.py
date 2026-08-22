from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .security import assert_safe_payload

APP_BUILDER_EVALUATOR_VERSION = "app-builder-observable-v1"
AppBuilderSuitePurpose = Literal["development", "promotion"]
AppBuilderCategory = Literal[
    "project_isolation",
    "spec_binding",
    "implementation_evidence",
    "build_test_verify_truth",
    "tool_authority",
    "interruption_recovery",
    "evidence_hygiene",
]
AppBuilderObservation = Annotated[str, Field(min_length=1, max_length=240)]
REQUIRED_APP_BUILDER_CATEGORIES = frozenset(
    {
        "project_isolation",
        "spec_binding",
        "implementation_evidence",
        "build_test_verify_truth",
        "tool_authority",
        "interruption_recovery",
        "evidence_hygiene",
    }
)


class AppBuilderStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppBuilderObservationRequirement(AppBuilderStrictModel):
    requirement_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    kind: Literal["required", "forbidden"]
    observation: AppBuilderObservation
    critical: bool = True


class AppBuilderBenchmarkCase(AppBuilderStrictModel):
    case_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    category: AppBuilderCategory
    objective: str = Field(min_length=1, max_length=2000)
    expected_project_ref: str | None = Field(default=None, min_length=1, max_length=160)
    expected_workspace_ref: str | None = Field(default=None, min_length=1, max_length=160)
    expected_spec_ref: str | None = Field(default=None, min_length=1, max_length=160)
    expected_spec_revision: int | None = Field(default=None, ge=1)
    expected_spec_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    minimum_evidence_digests: int = Field(default=0, ge=0, le=16)
    requirements: list[AppBuilderObservationRequirement] = Field(min_length=1, max_length=48)
    minimum_score: float = Field(ge=0.0, le=1.0)
    case_weight: float = Field(default=1.0, gt=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_requirements(self) -> "AppBuilderBenchmarkCase":
        ids = [item.requirement_id for item in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("observation requirement IDs must be unique within a case")
        normalized = [item.observation.strip().casefold() for item in self.requirements]
        if any(not value for value in normalized):
            raise ValueError("observation requirements may not be empty or whitespace-only")
        if len(normalized) != len(set(normalized)):
            raise ValueError("observation requirements may not duplicate or contradict one another")
        return self


class AppBuilderBenchmarkSuite(AppBuilderStrictModel):
    schema_version: Literal["1"]
    suite_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    suite_version: str = Field(pattern=r"^v\d+\.\d+$")
    spec_id: str = Field(pattern=r"^P2-V\d+\.\d+\.\d+$")
    purpose: AppBuilderSuitePurpose
    minimum_aggregate_score: float = Field(ge=0.0, le=1.0)
    category_minimums: dict[AppBuilderCategory, float]
    cases: list[AppBuilderBenchmarkCase] = Field(min_length=7, max_length=200)

    @model_validator(mode="after")
    def validate_suite(self) -> "AppBuilderBenchmarkSuite":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("app-builder suite contains duplicate case IDs")
        case_categories = {case.category for case in self.cases}
        if case_categories != REQUIRED_APP_BUILDER_CATEGORIES:
            missing = sorted(REQUIRED_APP_BUILDER_CATEGORIES - case_categories)
            extra = sorted(case_categories - REQUIRED_APP_BUILDER_CATEGORIES)
            raise ValueError(f"app-builder suite categories mismatch; missing={missing}, extra={extra}")
        if set(self.category_minimums) != REQUIRED_APP_BUILDER_CATEGORIES:
            missing = sorted(REQUIRED_APP_BUILDER_CATEGORIES - set(self.category_minimums))
            extra = sorted(set(self.category_minimums) - REQUIRED_APP_BUILDER_CATEGORIES)
            raise ValueError(f"category floors mismatch; missing={missing}, extra={extra}")
        for category, value in self.category_minimums.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"category threshold out of range: {category}")
        return self


class AppBuilderCaseEvidence(AppBuilderStrictModel):
    case_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    project_ref: str = Field(min_length=1, max_length=160)
    workspace_ref: str | None = Field(default=None, min_length=1, max_length=160)
    spec_ref: str | None = Field(default=None, min_length=1, max_length=160)
    spec_revision: int | None = Field(default=None, ge=1)
    spec_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    run_ref: str | None = Field(default=None, min_length=1, max_length=160)
    observations: list[AppBuilderObservation] = Field(default_factory=list, max_length=96)
    evidence_digests: list[str] = Field(default_factory=list, max_length=16)
    no_chain_of_thought: Literal[True] = True

    @model_validator(mode="after")
    def validate_evidence(self) -> "AppBuilderCaseEvidence":
        normalized = [value.strip().casefold() for value in self.observations]
        if any(not value for value in normalized):
            raise ValueError("observations may not contain empty values")
        if len(normalized) != len(set(normalized)):
            raise ValueError("observations must be unique within a case")
        for digest in self.evidence_digests:
            if not _is_digest(digest):
                raise ValueError("evidence digests must use sha256:<64 lowercase hex>")
        if len(self.evidence_digests) != len(set(self.evidence_digests)):
            raise ValueError("evidence digests must be unique within a case")
        return self


class AppBuilderRecordedEvidence(AppBuilderStrictModel):
    evidence_version: Literal["1"]
    artifact_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    suite_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    suite_version: str = Field(pattern=r"^v\d+\.\d+$")
    suite_purpose: AppBuilderSuitePurpose
    candidate_version: str = Field(min_length=1, max_length=200)
    model_id: str | None = Field(default=None, max_length=200)
    cases: list[AppBuilderCaseEvidence] = Field(min_length=1, max_length=200)
    no_chain_of_thought: Literal[True] = True

    @model_validator(mode="after")
    def validate_case_ids(self) -> "AppBuilderRecordedEvidence":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("recorded evidence contains duplicate case IDs")
        return self


class AppBuilderCaseResult(AppBuilderStrictModel):
    case_id: str
    category: AppBuilderCategory
    score: float = Field(ge=0.0, le=1.0)
    minimum_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    critical_failure: bool
    checks_passed: int = Field(ge=0)
    checks_total: int = Field(ge=1)
    failures: list[str]
    evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class AppBuilderCategoryResult(AppBuilderStrictModel):
    category: AppBuilderCategory
    score: float = Field(ge=0.0, le=1.0)
    minimum_score: float = Field(ge=0.0, le=1.0)
    passed: bool


class AppBuilderEvaluationReport(AppBuilderStrictModel):
    report_version: Literal["1"] = "1"
    report_id: str = Field(pattern=r"^app-eval-[0-9a-f]{16}$")
    spec_id: str
    suite_id: str
    suite_version: str
    suite_purpose: AppBuilderSuitePurpose
    evaluator_version: Literal["app-builder-observable-v1"] = APP_BUILDER_EVALUATOR_VERSION
    candidate_artifact_id: str
    candidate_version: str
    candidate_model_id: str | None = None
    input_evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    case_results: list[AppBuilderCaseResult]
    category_results: list[AppBuilderCategoryResult]
    aggregate_score: float = Field(ge=0.0, le=1.0)
    minimum_aggregate_score: float = Field(ge=0.0, le=1.0)
    protected_pass: bool
    no_chain_of_thought: Literal[True] = True


def _is_digest(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != 71:
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return value[7:] == value[7:].lower()


def canonical_digest(payload: object) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _read_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_app_builder_suite(path: str | Path) -> AppBuilderBenchmarkSuite:
    payload = _read_json(path)
    assert_safe_payload(payload)
    return AppBuilderBenchmarkSuite.model_validate(payload)


def load_app_builder_evidence(path: str | Path) -> AppBuilderRecordedEvidence:
    payload = _read_json(path)
    assert_safe_payload(payload)
    return AppBuilderRecordedEvidence.model_validate(payload)


def _binding_checks(case: AppBuilderBenchmarkCase, evidence: AppBuilderCaseEvidence) -> list[tuple[str, bool, bool]]:
    checks: list[tuple[str, bool, bool]] = []
    expected = (
        ("project_ref", case.expected_project_ref, evidence.project_ref),
        ("workspace_ref", case.expected_workspace_ref, evidence.workspace_ref),
        ("spec_ref", case.expected_spec_ref, evidence.spec_ref),
        ("spec_revision", case.expected_spec_revision, evidence.spec_revision),
        ("spec_digest", case.expected_spec_digest, evidence.spec_digest),
    )
    for field_name, expected_value, actual_value in expected:
        if expected_value is not None:
            checks.append((f"binding_mismatch:{field_name}", actual_value == expected_value, True))
    if case.minimum_evidence_digests:
        checks.append(
            (
                f"insufficient_evidence_digests:{len(evidence.evidence_digests)}<{case.minimum_evidence_digests}",
                len(evidence.evidence_digests) >= case.minimum_evidence_digests,
                True,
            )
        )
    return checks


def evaluate_app_builder_case(
    case: AppBuilderBenchmarkCase,
    evidence: AppBuilderCaseEvidence,
) -> AppBuilderCaseResult:
    checks = _binding_checks(case, evidence)
    observations = {item.strip().casefold() for item in evidence.observations}
    for requirement in case.requirements:
        present = requirement.observation.strip().casefold() in observations
        if requirement.kind == "required":
            checks.append((f"missing_required:{requirement.requirement_id}", present, requirement.critical))
        else:
            checks.append((f"forbidden_present:{requirement.requirement_id}", not present, requirement.critical))

    failures = [code for code, passed, _critical in checks if not passed]
    critical_failure = any(not passed and critical for _code, passed, critical in checks)
    passed_checks = sum(1 for _code, passed, _critical in checks if passed)
    total_checks = len(checks)
    score = passed_checks / total_checks
    if score < case.minimum_score:
        failures.append(f"below_case_threshold:{score:.4f}<{case.minimum_score:.4f}")
    passed = not critical_failure and score >= case.minimum_score
    return AppBuilderCaseResult(
        case_id=case.case_id,
        category=case.category,
        score=score,
        minimum_score=case.minimum_score,
        passed=passed,
        critical_failure=critical_failure,
        checks_passed=passed_checks,
        checks_total=total_checks,
        failures=failures,
        evidence_digest=canonical_digest(evidence),
    )


def evaluate_app_builder(
    suite: AppBuilderBenchmarkSuite,
    evidence: AppBuilderRecordedEvidence,
) -> AppBuilderEvaluationReport:
    assert_safe_payload(suite)
    assert_safe_payload(evidence)
    if evidence.suite_id != suite.suite_id or evidence.suite_version != suite.suite_version:
        raise ValueError("recorded evidence suite identity does not match app-builder suite")
    if evidence.suite_purpose != suite.purpose:
        raise ValueError("recorded evidence suite purpose does not match app-builder suite")

    case_by_id = {case.case_id: case for case in suite.cases}
    evidence_by_id = {case.case_id: case for case in evidence.cases}
    unknown = sorted(set(evidence_by_id) - set(case_by_id))
    missing = sorted(set(case_by_id) - set(evidence_by_id))
    if unknown:
        raise ValueError(f"recorded evidence contains unknown cases: {unknown}")
    if missing:
        raise ValueError(f"recorded evidence is missing cases: {missing}")

    case_results = [evaluate_app_builder_case(case, evidence_by_id[case.case_id]) for case in suite.cases]
    result_by_id = {result.case_id: result for result in case_results}

    category_results: list[AppBuilderCategoryResult] = []
    for category in sorted(REQUIRED_APP_BUILDER_CATEGORIES):
        members = [case for case in suite.cases if case.category == category]
        total_weight = sum(case.case_weight for case in members)
        score = sum(result_by_id[case.case_id].score * case.case_weight for case in members) / total_weight
        floor = suite.category_minimums[category]  # type: ignore[index]
        category_results.append(
            AppBuilderCategoryResult(
                category=category,  # type: ignore[arg-type]
                score=score,
                minimum_score=floor,
                passed=score >= floor and all(result_by_id[case.case_id].passed for case in members),
            )
        )

    total_weight = sum(case.case_weight for case in suite.cases)
    aggregate = sum(result_by_id[case.case_id].score * case.case_weight for case in suite.cases) / total_weight
    protected_pass = (
        aggregate >= suite.minimum_aggregate_score
        and all(result.passed for result in case_results)
        and all(result.passed for result in category_results)
    )
    input_digest = canonical_digest(evidence)
    report = AppBuilderEvaluationReport(
        report_id=f"app-eval-{input_digest[7:23]}",
        spec_id=suite.spec_id,
        suite_id=suite.suite_id,
        suite_version=suite.suite_version,
        suite_purpose=suite.purpose,
        candidate_artifact_id=evidence.artifact_id,
        candidate_version=evidence.candidate_version,
        candidate_model_id=evidence.model_id,
        input_evidence_digest=input_digest,
        case_results=case_results,
        category_results=category_results,
        aggregate_score=aggregate,
        minimum_aggregate_score=suite.minimum_aggregate_score,
        protected_pass=protected_pass,
    )
    assert_safe_payload(report)
    return report


def write_app_builder_report(report: AppBuilderEvaluationReport, path: str | Path) -> Path:
    assert_safe_payload(report)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target
