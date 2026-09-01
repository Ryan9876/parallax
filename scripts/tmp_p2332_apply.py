from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected exactly one replacement anchor, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1))


# Server-owned static-web reason vocabulary is the single source for repair classification.
replace_once(
    "services/api/parallax_api/code/static_web_validator.py",
    '_IGNORED_SCHEMES = frozenset({"http", "https", "data", "mailto", "tel"})\n',
    '''_IGNORED_SCHEMES = frozenset({"http", "https", "data", "mailto", "tel"})\n\nSTATIC_WEB_VALIDATION_REASON_CODES = frozenset(\n    {\n        "STATIC_WEB_ARGUMENTS_INVALID",\n        "STATIC_WEB_ROOT_INVALID",\n        "STATIC_WEB_SYMLINK_REJECTED",\n        "STATIC_WEB_SPECIAL_FILE_REJECTED",\n        "STATIC_WEB_PATH_ESCAPE",\n        "STATIC_WEB_INDEX_REQUIRED",\n        "STATIC_WEB_INDEX_ESCAPE",\n        "STATIC_WEB_JS_CHECK_UNAVAILABLE",\n        "STATIC_WEB_JS_SYNTAX_INVALID",\n        "STATIC_WEB_REFERENCE_SCHEME_UNSUPPORTED",\n        "STATIC_WEB_REFERENCE_PATH_INVALID",\n        "STATIC_WEB_INDEX_NOT_UTF8",\n        "STATIC_WEB_HTML_INVALID",\n        "STATIC_WEB_LOCAL_REFERENCE_MISSING",\n        "STATIC_WEB_REFERENCE_PATH_ESCAPE",\n        "STATIC_WEB_STAGE_INVALID",\n    }\n)\nSTATIC_WEB_REPAIRABLE_REASON_CODES = frozenset(\n    {\n        "STATIC_WEB_INDEX_REQUIRED",\n        "STATIC_WEB_JS_SYNTAX_INVALID",\n        "STATIC_WEB_REFERENCE_SCHEME_UNSUPPORTED",\n        "STATIC_WEB_REFERENCE_PATH_INVALID",\n        "STATIC_WEB_INDEX_NOT_UTF8",\n        "STATIC_WEB_HTML_INVALID",\n        "STATIC_WEB_LOCAL_REFERENCE_MISSING",\n    }\n)\n''',
)

# Candidate runtime: extract only a fixed server-owned reason and reuse the existing second candidate round.
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    "from dataclasses import dataclass\n",
    "from dataclasses import dataclass, replace\n",
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    "from .service import EngineeringRunService\n",
    '''from .service import EngineeringRunService\nfrom .static_web_validator import (\n    STATIC_WEB_REPAIRABLE_REASON_CODES,\n    STATIC_WEB_VALIDATION_REASON_CODES,\n)\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    "    ExecutionContract,\n",
    "    ExecutionContract,\n    ExecutionContractCode,\n",
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    'AGENTIC_RUNTIME_VERSION = "agentic-runtime-v0.19.8"\n',
    'AGENTIC_RUNTIME_VERSION = "agentic-runtime-v0.19.9"\n',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''def _sha256_value(value: object) -> str | None:\n    if (\n        isinstance(value, str)\n        and len(value) == 64\n        and all(ch in "0123456789abcdef" for ch in value)\n    ):\n        return value\n    return None\n\n\ndef _candidate_validation_failure_diagnostic(\n''',
    '''def _sha256_value(value: object) -> str | None:\n    if (\n        isinstance(value, str)\n        and len(value) == 64\n        and all(ch in "0123456789abcdef" for ch in value)\n    ):\n        return value\n    return None\n\n\ndef _static_web_validation_reason(value: object) -> str | None:\n    """Project exactly one fixed server-owned static-web validator reason."""\n\n    if not isinstance(value, str):\n        return None\n    clean = value.strip()\n    if not clean or len(clean.splitlines()) != 1:\n        return None\n    return clean if clean in STATIC_WEB_VALIDATION_REASON_CODES else None\n\n\ndef _candidate_validation_failure_diagnostic(\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''    content_digest = _sha256_value(validation.content_digest)\n    if content_digest is not None:\n        diagnostic["candidate_content_digest"] = content_digest\n''',
    '''    reason_code = evidence.get("validation_reason_code")\n    if reason_code in STATIC_WEB_VALIDATION_REASON_CODES:\n        diagnostic["validation_reason_code"] = reason_code\n\n    content_digest = _sha256_value(validation.content_digest)\n    if content_digest is not None:\n        diagnostic["candidate_content_digest"] = content_digest\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''                        result = instance.run_process(\n                            command,\n                            list(args),\n                            cwd=self._sandbox_cwd(spec.working_directory),\n                            env={},\n                            kill_after=spec.timeout_seconds,\n                            capture_output=True,\n                        )\n                        evidence = _bounded_evidence(\n                            spec,\n                            exit_code=result.returncode,\n                            duration_ms=int((time.monotonic() - started) * 1000),\n                            stdout=result.stdout or "",\n                            stderr=result.stderr or "",\n                        )\n''',
    '''                        result = instance.run_process(\n                            command,\n                            list(args),\n                            cwd=self._sandbox_cwd(spec.working_directory),\n                            env={},\n                            kill_after=spec.timeout_seconds,\n                            capture_output=True,\n                        )\n                        raw_stderr = result.stderr or ""\n                        evidence = _bounded_evidence(\n                            spec,\n                            exit_code=result.returncode,\n                            duration_ms=int((time.monotonic() - started) * 1000),\n                            stdout=result.stdout or "",\n                            stderr=raw_stderr,\n                        )\n                        if profile.ecosystem == "static-web":\n                            reason_code = _static_web_validation_reason(raw_stderr)\n                            if reason_code is not None:\n                                evidence["validation_reason_code"] = reason_code\n''',
)

# Insert bounded replacement helpers immediately before generate_protected.
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''    def generate_protected(\n        self,\n        request: ImplementationGenerationRequest,\n''',
    '''    @staticmethod\n    def _candidate_validation_repairable(\n        diagnostic: dict[str, object],\n        execution_contract: ExecutionContract,\n    ) -> bool:\n        return (\n            execution_contract.contract_id is ExecutionContractCode.STATIC_WEB\n            and execution_contract.validation_profile.ecosystem == "static-web"\n            and diagnostic.get("failed_stage")\n            in {WorkflowStage.BUILD.value, WorkflowStage.TEST.value, WorkflowStage.VERIFY.value}\n            and diagnostic.get("validation_reason_code") in STATIC_WEB_REPAIRABLE_REASON_CODES\n            and diagnostic.get("timed_out") is False\n        )\n\n    @staticmethod\n    def _candidate_validation_repair_request(\n        request: ImplementationGenerationRequest,\n        execution_contract: ExecutionContract,\n        diagnostic: dict[str, object],\n    ) -> ImplementationGenerationRequest:\n        reason_code = diagnostic.get("validation_reason_code")\n        failed_stage = diagnostic.get("failed_stage")\n        if (\n            execution_contract.contract_id is not ExecutionContractCode.STATIC_WEB\n            or execution_contract.validation_profile.ecosystem != "static-web"\n            or reason_code not in STATIC_WEB_REPAIRABLE_REASON_CODES\n            or failed_stage not in {WorkflowStage.BUILD.value, WorkflowStage.TEST.value, WorkflowStage.VERIFY.value}\n        ):\n            raise AgenticRuntimeError("candidate validation repair guidance is not server-admitted")\n        fixed_guidance = (\n            "Server-owned candidate validation repair: the previous disposable candidate was rejected and is discarded. "\n            f"Protected {failed_stage} returned fixed static-web reason {reason_code}. "\n            "Produce one complete replacement proposal that independently covers every supplied acceptance ID under the "\n            "immutable static-web-v1 execution contract. The replacement must include a root index.html and only local "\n            "HTML, CSS, and JavaScript assets compatible with the server-owned static-web validator. Package managers, "\n            "bundlers, package scripts, arbitrary shell commands, and network fetches are unavailable. Do not reference "\n            "or rely on rejected candidate content or validator output beyond the fixed reason code supplied here."\n        )\n        return replace(request, constraints=(*request.constraints, fixed_guidance))\n\n    def _repair_failed_primary_candidate(\n        self,\n        *,\n        run: EngineeringRun,\n        primary: ProducedCandidate,\n        primary_plan: TeamPlan,\n        execution_contract: ExecutionContract,\n        execution_request: ImplementationGenerationRequest,\n        base_workspace: Path,\n        source_digest: str,\n        proposal_validator: Callable[[ImplementationProposal], bool],\n        operation_key: str,\n        routing_context: RoutingContext,\n    ) -> tuple[ProducedCandidate, dict[str, object]]:\n        diagnostic = _candidate_validation_failure_diagnostic(\n            primary.candidate_id,\n            primary.validation,\n        )\n        if diagnostic is None:\n            raise AgenticRuntimeError("failed primary candidate lacks bounded validation diagnostics")\n        if not self._candidate_validation_repairable(diagnostic, execution_contract):\n            raise CandidateValidationFailure(\n                "protected candidate validation failed without repairable server-owned reason",\n                diagnostic_evidence=diagnostic,\n            )\n        acceptance = self._acceptance(run, self.service)\n        repair_plan = self._challenger_plan(\n            run=run,\n            acceptance=acceptance,\n            source_digest=source_digest,\n            primary=primary_plan,\n        )\n        if repair_plan is None:\n            raise CandidateValidationFailure(\n                "protected candidate validation repair has no admitted alternative candidate",\n                diagnostic_evidence=diagnostic,\n            )\n        repair_request = self._candidate_validation_repair_request(\n            execution_request,\n            execution_contract,\n            diagnostic,\n        )\n        replacement, _ = self._make_candidate(\n            run=run,\n            primary_plan=primary_plan,\n            plan=repair_plan,\n            request=repair_request,\n            base_workspace=base_workspace,\n            validation_profile=execution_contract.validation_profile,\n            proposal_validator=proposal_validator,\n            operation_key=operation_key,\n            candidate_id="candidate-repair",\n            alternative_round=2,\n            routing_context=routing_context,\n        )\n        if not replacement.validation.passed:\n            replacement_diagnostic = _candidate_validation_failure_diagnostic(\n                replacement.candidate_id,\n                replacement.validation,\n            )\n            if replacement_diagnostic is None:\n                raise AgenticRuntimeError("failed replacement candidate lacks bounded validation diagnostics")\n            raise CandidateValidationFailure(\n                "bounded replacement candidate failed protected validation",\n                diagnostic_evidence=replacement_diagnostic,\n            )\n        return replacement, diagnostic\n\n    def generate_protected(\n        self,\n        request: ImplementationGenerationRequest,\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''            primary, routing_context = self._make_candidate(\n                run=run,\n                primary_plan=primary_plan,\n                plan=primary_plan,\n                request=execution_request,\n                base_workspace=workspace_root,\n                validation_profile=execution_contract.validation_profile,\n                proposal_validator=proposal_validator,\n                operation_key=operation_key,\n                candidate_id="candidate-primary",\n                alternative_round=1,\n            )\n            candidates = [primary]\n\n            competition_context = self._competition_context(\n''',
    '''            primary, routing_context = self._make_candidate(\n                run=run,\n                primary_plan=primary_plan,\n                plan=primary_plan,\n                request=execution_request,\n                base_workspace=workspace_root,\n                validation_profile=execution_contract.validation_profile,\n                proposal_validator=proposal_validator,\n                operation_key=operation_key,\n                candidate_id="candidate-primary",\n                alternative_round=1,\n            )\n            repair_used = False\n            repair_diagnostic: dict[str, object] | None = None\n            if primary.validation.passed:\n                candidates = [primary]\n            else:\n                replacement, repair_diagnostic = self._repair_failed_primary_candidate(\n                    run=run,\n                    primary=primary,\n                    primary_plan=primary_plan,\n                    execution_contract=execution_contract,\n                    execution_request=execution_request,\n                    base_workspace=workspace_root,\n                    source_digest=lineage.content_digest,\n                    proposal_validator=proposal_validator,\n                    operation_key=operation_key,\n                    routing_context=routing_context,\n                )\n                candidates = [replacement]\n                repair_used = True\n\n            competition_context = self._competition_context(\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''            signal = None\n            if len(primary_plan.selected_agent_digests) > 1:\n''',
    '''            signal = None\n            if not repair_used and len(primary_plan.selected_agent_digests) > 1:\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''            if trigger is CompetitionTriggerDisposition.COMPETE:\n''',
    '''            if not repair_used and trigger is CompetitionTriggerDisposition.COMPETE:\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''                "candidate_count": len(candidates),\n                "candidates": [\n''',
    '''                "candidate_count": len(candidates),\n                "candidate_generation_count": 2 if repair_used else len(candidates),\n                "validation_repair_used": repair_used,\n                "validation_repair_reason_code": (\n                    repair_diagnostic.get("validation_reason_code")\n                    if repair_diagnostic is not None\n                    else None\n                ),\n                "rejected_candidate_content_digest": (\n                    primary.validation.content_digest if repair_used else None\n                ),\n                "candidates": [\n''',
)
replace_once(
    "services/api/parallax_api/code/agentic_runtime.py",
    '''                "parallax_candidate_validation_failed candidate=%s stage=%s timed_out=%s",\n                diagnostic.get("candidate_id"),\n                diagnostic.get("failed_stage"),\n                diagnostic.get("timed_out") is True,\n''',
    '''                "parallax_candidate_validation_failed candidate=%s stage=%s reason=%s timed_out=%s",\n                diagnostic.get("candidate_id"),\n                diagnostic.get("failed_stage"),\n                diagnostic.get("validation_reason_code"),\n                diagnostic.get("timed_out") is True,\n''',
)

# Durable failure sanitizer: only the server-owned fixed reason vocabulary is accepted.
replace_once(
    "services/api/parallax_api/code/implementation_runtime.py",
    "from .state_machine import RevisionConflict\n",
    '''from .state_machine import RevisionConflict\nfrom .static_web_validator import STATIC_WEB_VALIDATION_REASON_CODES\n''',
)
replace_once(
    "services/api/parallax_api/code/implementation_runtime.py",
    '''        "candidate_content_digest",\n        "candidate_is_canonical_lineage",\n''',
    '''        "candidate_content_digest",\n        "validation_reason_code",\n        "candidate_is_canonical_lineage",\n''',
)
replace_once(
    "services/api/parallax_api/code/implementation_runtime.py",
    '''    if "validation_profile_digest" in raw:\n        digest = raw["validation_profile_digest"]\n''',
    '''    if "validation_reason_code" in raw:\n        reason_code = raw["validation_reason_code"]\n        if reason_code not in STATIC_WEB_VALIDATION_REASON_CODES:\n            raise ValueError("candidate validation diagnostics contain an invalid fixed validator reason")\n        normalized_failure["validation_reason_code"] = reason_code\n\n    if "validation_profile_digest" in raw:\n        digest = raw["validation_profile_digest"]\n''',
)

# The release canary was already static-web. Make that contract identity explicit in the safe build log.
replace_once(
    "services/api/scripts/production_candidate_validation_canary.py",
    '''    print(\n        "Production candidate-validation canary: PASS "\n        f"(profile={result.validation_profile_id}; stages=BUILD,TEST,VERIFY; "\n        f"candidate_digest={result.content_digest})"\n    )\n''',
    '''    print(\n        "Production candidate-validation canary: PASS "\n        "(contract=static-web-v1; binding=GREENFIELD_STATIC_WEB; ecosystem=static-web; "\n        f"profile={result.validation_profile_id}; stages=BUILD,TEST,VERIFY; "\n        f"candidate_digest={result.content_digest})"\n    )\n''',
)

# Focused regression coverage.
Path("services/api/tests/test_candidate_validation_repair_v02332.py").write_text(r'''from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from parallax_api.code.agentic_runtime import (
    AgenticControlPlane,
    CandidateValidationFailure,
    CandidateValidationResult,
    _candidate_validation_failure_diagnostic,
    _static_web_validation_reason,
)
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.implementation_runtime import _bounded_implementation_failure_evidence
from parallax_api.code.static_web_validator import (
    STATIC_WEB_REPAIRABLE_REASON_CODES,
    STATIC_WEB_VALIDATION_REASON_CODES,
)
from parallax_api.code.validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    resolve_execution_contract,
)
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    ImplementationGenerationRequest,
)


def _validation(reason: str, *, passed: bool = False) -> CandidateValidationResult:
    evidence = {
        "protected_success": passed,
        "exit_code": 0 if passed else 1,
        "timed_out": False,
        "validation_reason_code": reason,
        "validation_profile_id": "node-v1",
        "validation_profile_digest": "a" * 64,
        "candidate_is_canonical_lineage": False,
        "accepts_source_lineage": False,
    }
    return CandidateValidationResult(
        content_digest="b" * 64,
        file_count=1,
        total_bytes=10,
        validation_profile_id="node-v1",
        validation_profile_digest="a" * 64,
        stage_evidence=((WorkflowStage.BUILD.value, evidence),),
    )


def _request() -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id="spec",
        work_specification_revision=1,
        work_specification_digest="c" * 64,
        title="Build a static page",
        objective="Build a static page",
        constraints=("Use bounded source changes.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="A page exists."),),
        source_context=SourceContextSnapshot(files=(), digest="d" * 64, total_bytes=0),
    )


def _contract():
    return resolve_execution_contract(
        ExecutionContractCode.STATIC_WEB.value,
        binding_reason=ExecutionBindingReason.GREENFIELD_STATIC_WEB.value,
        target=None,
    )


def test_static_web_reason_projection_is_exact_and_closed():
    assert _static_web_validation_reason("STATIC_WEB_INDEX_REQUIRED\n") == "STATIC_WEB_INDEX_REQUIRED"
    assert _static_web_validation_reason("STATIC_WEB_INDEX_REQUIRED\nsecret") is None
    assert _static_web_validation_reason("prefix STATIC_WEB_INDEX_REQUIRED") is None
    assert _static_web_validation_reason("UNKNOWN") is None
    assert STATIC_WEB_REPAIRABLE_REASON_CODES < STATIC_WEB_VALIDATION_REASON_CODES


def test_candidate_failure_diagnostic_and_durable_sanitizer_admit_only_fixed_reason():
    diagnostic = _candidate_validation_failure_diagnostic("candidate-primary", _validation("STATIC_WEB_INDEX_REQUIRED"))
    assert diagnostic is not None
    assert diagnostic["validation_reason_code"] == "STATIC_WEB_INDEX_REQUIRED"
    normalized = _bounded_implementation_failure_evidence({"candidate_validation_failure": diagnostic})
    assert normalized["candidate_validation_failure"]["validation_reason_code"] == "STATIC_WEB_INDEX_REQUIRED"

    tampered = dict(diagnostic)
    tampered["validation_reason_code"] = "RAW STDERR secret"
    with pytest.raises(ValueError):
        _bounded_implementation_failure_evidence({"candidate_validation_failure": tampered})


def test_repair_request_contains_only_fixed_server_guidance():
    diagnostic = _candidate_validation_failure_diagnostic("candidate-primary", _validation("STATIC_WEB_INDEX_REQUIRED"))
    assert diagnostic is not None
    repaired = AgenticControlPlane._candidate_validation_repair_request(_request(), _contract(), diagnostic)
    assert repaired.source_context is _request().source_context or repaired.source_context.files == ()
    assert len(repaired.constraints) == 2
    guidance = repaired.constraints[-1]
    assert "STATIC_WEB_INDEX_REQUIRED" in guidance
    assert "static-web-v1" in guidance
    assert "stderr" not in guidance.casefold()
    assert "secret" not in guidance.casefold()


class _RepairHarness(AgenticControlPlane):
    def __init__(self, replacement):
        self.service = object()
        self.replacement = replacement
        self.calls = []

    @staticmethod
    def _acceptance(run, service):
        return ({"id": "AC-01", "text": "A page exists."},)

    def _challenger_plan(self, **kwargs):
        return SimpleNamespace(selected_agent_digests=("agent-b",), plan_id="repair-plan")

    def _make_candidate(self, **kwargs):
        self.calls.append(kwargs)
        return self.replacement, kwargs["routing_context"]


def test_repair_uses_existing_second_round_and_restarts_from_authoritative_base(tmp_path: Path):
    primary = SimpleNamespace(
        candidate_id="candidate-primary",
        validation=_validation("STATIC_WEB_INDEX_REQUIRED"),
    )
    replacement = SimpleNamespace(
        candidate_id="candidate-repair",
        validation=CandidateValidationResult(
            content_digest="e" * 64,
            file_count=1,
            total_bytes=20,
            validation_profile_id="node-v1",
            validation_profile_digest="a" * 64,
            stage_evidence=(
                (WorkflowStage.BUILD.value, {"protected_success": True}),
                (WorkflowStage.TEST.value, {"protected_success": True}),
                (WorkflowStage.VERIFY.value, {"protected_success": True}),
            ),
        ),
    )
    control = _RepairHarness(replacement)
    base = tmp_path / "base"
    base.mkdir()
    repaired, diagnostic = control._repair_failed_primary_candidate(
        run=SimpleNamespace(),
        primary=primary,
        primary_plan=SimpleNamespace(selected_agent_digests=("agent-a",)),
        execution_contract=_contract(),
        execution_request=_request(),
        base_workspace=base,
        source_digest="f" * 64,
        proposal_validator=lambda proposal: True,
        operation_key="repair-test",
        routing_context=SimpleNamespace(),
    )
    assert repaired is replacement
    assert diagnostic["validation_reason_code"] == "STATIC_WEB_INDEX_REQUIRED"
    assert len(control.calls) == 1
    call = control.calls[0]
    assert call["candidate_id"] == "candidate-repair"
    assert call["alternative_round"] == 2
    assert call["base_workspace"] == base
    assert "STATIC_WEB_INDEX_REQUIRED" in call["request"].constraints[-1]


def test_nonrepairable_reason_does_not_generate_replacement(tmp_path: Path):
    primary = SimpleNamespace(
        candidate_id="candidate-primary",
        validation=_validation("STATIC_WEB_JS_CHECK_UNAVAILABLE"),
    )
    control = _RepairHarness(SimpleNamespace())
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(CandidateValidationFailure):
        control._repair_failed_primary_candidate(
            run=SimpleNamespace(),
            primary=primary,
            primary_plan=SimpleNamespace(selected_agent_digests=("agent-a",)),
            execution_contract=_contract(),
            execution_request=_request(),
            base_workspace=base,
            source_digest="f" * 64,
            proposal_validator=lambda proposal: True,
            operation_key="repair-test",
            routing_context=SimpleNamespace(),
        )
    assert control.calls == []


def test_second_candidate_validation_rejection_is_terminal(tmp_path: Path):
    primary = SimpleNamespace(
        candidate_id="candidate-primary",
        validation=_validation("STATIC_WEB_INDEX_REQUIRED"),
    )
    replacement = SimpleNamespace(
        candidate_id="candidate-repair",
        validation=_validation("STATIC_WEB_JS_SYNTAX_INVALID"),
    )
    control = _RepairHarness(replacement)
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(CandidateValidationFailure) as captured:
        control._repair_failed_primary_candidate(
            run=SimpleNamespace(),
            primary=primary,
            primary_plan=SimpleNamespace(selected_agent_digests=("agent-a",)),
            execution_contract=_contract(),
            execution_request=_request(),
            base_workspace=base,
            source_digest="f" * 64,
            proposal_validator=lambda proposal: True,
            operation_key="repair-test",
            routing_context=SimpleNamespace(),
        )
    assert captured.value.diagnostic_evidence["candidate_id"] == "candidate-repair"
    assert len(control.calls) == 1
''')
