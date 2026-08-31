from __future__ import annotations

from pathlib import Path


def replace_exact(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{path}: expected {count} occurrences, found {found}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


# AC-02: after a bounded step, classify the new authoritative state before
# falling back to MAX_STEPS_REACHED.
replace_exact(
    "services/api/parallax_api/code/autonomy.py",
    '''        return AutonomyResult(\n            run=self.service.get(run_id),\n            stop_reason=AutonomyStopReason.MAX_STEPS_REACHED,\n            steps=tuple(steps),\n        )\n''',
    '''        run = self.service.get(run_id)\n        terminal_reason = self._stop_reason(WorkflowStage(run.state))\n        return AutonomyResult(\n            run=run,\n            stop_reason=terminal_reason or AutonomyStopReason.MAX_STEPS_REACHED,\n            steps=tuple(steps),\n        )\n''',
)

# AC-01: make the coordinator step budget an explicit composition input.
replace_exact(
    "services/api/parallax_api/code/runtime_composition.py",
    '''        *,\n        lineage_executor: LineageAwareAutonomousExecutor | None = None,\n        source_delivery: SourceDeliveryComposition | None = None,\n    ) -> None:\n''',
    '''        *,\n        lineage_executor: LineageAwareAutonomousExecutor | None = None,\n        source_delivery: SourceDeliveryComposition | None = None,\n        max_steps: int = 8,\n    ) -> None:\n''',
)
replace_exact(
    "services/api/parallax_api/code/runtime_composition.py",
    '''            implementation_runtime=self.implementation_runtime,\n            lineage_executor=lineage_executor,\n        )\n''',
    '''            implementation_runtime=self.implementation_runtime,\n            lineage_executor=lineage_executor,\n            max_steps=max_steps,\n        )\n''',
)

# Propagate the bounded request budget through both live agentic builders.
replace_exact(
    "services/api/parallax_api/code/agentic_runtime_live.py",
    '''    candidate_validator: CandidateValidationExecutor | None = None,\n    adapters: tuple[HostedImplementationAgent, ...] | None = None,\n    candidate_objects: ImmutableObjectStore | None = None,\n) -> EngineeringRuntimeComposition:\n''',
    '''    candidate_validator: CandidateValidationExecutor | None = None,\n    adapters: tuple[HostedImplementationAgent, ...] | None = None,\n    candidate_objects: ImmutableObjectStore | None = None,\n    max_steps: int = 8,\n) -> EngineeringRuntimeComposition:\n''',
)
replace_exact(
    "services/api/parallax_api/code/agentic_runtime_live.py",
    '''        lineage_executor=lineage_executor,\n        source_delivery=source_delivery,\n    )\n''',
    '''        lineage_executor=lineage_executor,\n        source_delivery=source_delivery,\n        max_steps=max_steps,\n    )\n''',
)
replace_exact(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    '''    candidate_validator: CandidateValidationExecutor | None = None,\n    adapters: tuple[HostedImplementationAgent, ...] | None = None,\n    candidate_objects: ImmutableObjectStore | None = None,\n) -> EngineeringRuntimeComposition:\n''',
    '''    candidate_validator: CandidateValidationExecutor | None = None,\n    adapters: tuple[HostedImplementationAgent, ...] | None = None,\n    candidate_objects: ImmutableObjectStore | None = None,\n    max_steps: int = 8,\n) -> EngineeringRuntimeComposition:\n''',
)
replace_exact(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    '''        lineage_executor=lineage_executor,\n        source_delivery=source_delivery,\n    )\n''',
    '''        lineage_executor=lineage_executor,\n        source_delivery=source_delivery,\n        max_steps=max_steps,\n    )\n''',
)

# Pin ordinary production autonomy to one protected lifecycle transition per
# HTTP invocation. The browser may request another transition only from the
# returned canonical revision.
replace_exact(
    "services/api/parallax_api/routes/engineering_runs.py",
    '''_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"\n_AGENTIC_RUNTIME_ENABLE_ENV = "PARALLAX_AGENTIC_RUNTIME_ENABLED"\n''',
    '''_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"\n_AGENTIC_RUNTIME_ENABLE_ENV = "PARALLAX_AGENTIC_RUNTIME_ENABLED"\n_AUTONOMY_REQUEST_MAX_STEPS = 1\n''',
)
replace_exact(
    "services/api/parallax_api/routes/engineering_runs.py",
    '''        runtime = AutonomyCoordinator(svc, legacy_executor)\n''',
    '''        runtime = AutonomyCoordinator(\n            svc,\n            legacy_executor,\n            max_steps=_AUTONOMY_REQUEST_MAX_STEPS,\n        )\n''',
)
replace_exact(
    "services/api/parallax_api/routes/engineering_runs.py",
    '''                    legacy_executor,\n                    source_delivery=source_delivery,\n                )\n''',
    '''                    legacy_executor,\n                    source_delivery=source_delivery,\n                    max_steps=_AUTONOMY_REQUEST_MAX_STEPS,\n                )\n''',
)
replace_exact(
    "services/api/parallax_api/routes/engineering_runs.py",
    '''                legacy_executor,\n                source_delivery=source_delivery,\n            )\n''',
    '''                legacy_executor,\n                source_delivery=source_delivery,\n                max_steps=_AUTONOMY_REQUEST_MAX_STEPS,\n            )\n''',
)

# AC-06: bound production hosted model calls. Explicit candidate recovery is
# the governed retry mechanism; hidden transport retries are disabled.
replace_exact(
    "services/api/parallax_api/intelligence/dspy_programs.py",
    '''_GATEWAY_MODEL_PREFIX = "vercel_ai_gateway/"\n''',
    '''_GATEWAY_MODEL_PREFIX = "vercel_ai_gateway/"\n_HOSTED_MODEL_TIMEOUT_SECONDS = 60\n_HOSTED_MODEL_NUM_RETRIES = 0\n''',
)
replace_exact(
    "services/api/parallax_api/intelligence/dspy_programs.py",
    '''            if gateway_key is not None and model.startswith("openai/"):\n                kwargs["api_base"] = _GATEWAY_API_BASE\n                kwargs["api_key"] = gateway_key\n                logger.info("parallax_model_transport transport=vercel_ai_gateway model=%s", model)\n''',
    '''            if gateway_key is not None and model.startswith("openai/"):\n                kwargs["api_base"] = _GATEWAY_API_BASE\n                kwargs["api_key"] = gateway_key\n                if _production_runtime():\n                    kwargs["timeout"] = _HOSTED_MODEL_TIMEOUT_SECONDS\n                    kwargs["num_retries"] = _HOSTED_MODEL_NUM_RETRIES\n                logger.info("parallax_model_transport transport=vercel_ai_gateway model=%s", model)\n''',
)

# AC-04/05: use DSPy's explicit JSON adapter and typed output fields rather
# than asking the model to encode the protected proposal inside a free string.
replace_exact(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    '''            proposal_json: str = dspy.OutputField(desc=IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT)\n''',
    '''            acceptance_ids_covered: list[str] = dspy.OutputField(\n                desc="exact supplied acceptance IDs in the same order"\n            )\n            patches: list[GeneratedSourcePatch] = dspy.OutputField(\n                desc=IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT\n            )\n''',
)
replace_exact(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    '''        self._program = dspy.Predict(GenerateImplementation)\n\n    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:\n        contract_json = json.dumps(request.contract_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))\n        source_json = json.dumps(request.source_prompt_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))\n        with self._dspy.context(lm=self._lm):\n            prediction = self._program(\n                work_specification_json=contract_json,\n                source_context_json=source_json,\n            )\n        try:\n            return ImplementationProposal.model_validate_json(str(prediction.proposal_json))\n        except ValidationError:\n            # Do not retain the Pydantic exception as an explicit cause because\n            # its in-memory details may include rejected model output. The typed\n            # boundary intentionally carries only fixed server-owned text.\n            raise ModelOutputValidationError(\n                "protected implementation proposal failed structured-output validation"\n            ) from None\n''',
    '''        self._program = dspy.Predict(GenerateImplementation)\n\n    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:\n        contract_json = json.dumps(request.contract_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))\n        source_json = json.dumps(request.source_prompt_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))\n        try:\n            with self._dspy.context(lm=self._lm, adapter=self._dspy.JSONAdapter()):\n                prediction = self._program(\n                    work_specification_json=contract_json,\n                    source_context_json=source_json,\n                )\n        except Exception as exc:\n            # DSPy raises AdapterParseError when a provider response cannot be\n            # decoded into the declared typed output. Keep provider/transport\n            # exceptions distinct so routing classification remains truthful.\n            if type(exc).__name__ == "AdapterParseError":\n                raise ModelOutputValidationError(\n                    "protected implementation proposal failed structured-output validation"\n                ) from None\n            raise\n        try:\n            return ImplementationProposal.model_validate(\n                {\n                    "acceptance_ids_covered": prediction.acceptance_ids_covered,\n                    "patches": prediction.patches,\n                }\n            )\n        except (ValidationError, TypeError, ValueError):\n            # Rejected typed data may contain model output. Do not retain the\n            # Pydantic exception or raw prediction across this boundary.\n            raise ModelOutputValidationError(\n                "protected implementation proposal failed structured-output validation"\n            ) from None\n''',
)
replace_exact(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    '''    version = "implementation-generation-v0.23.15"\n''',
    '''    version = "implementation-generation-v0.23.22"\n''',
)

# AC-03: centralize the finite browser continuation policy.
Path("apps/client/src/state/engineeringRunContinuation.ts").write_text(
    '''export const AUTONOMOUS_ENGINEERING_RUN_STATES = ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY'] as const;\nexport const MAX_AUTONOMY_REQUESTS_PER_CONTINUATION = 8;\n\nconst autonomousStates = new Set<string>(AUTONOMOUS_ENGINEERING_RUN_STATES);\n\nexport type EngineeringRunContinuationIdentity = {\n  id: string;\n  revision: number;\n  state: string;\n  binding_status: string;\n};\n\nexport type AutonomyContinuationDisposition = 'CONTINUE' | 'STOP' | 'LIMIT_REACHED';\n\nexport function canContinueEngineeringRunAutonomously(run: EngineeringRunContinuationIdentity): boolean {\n  return run.binding_status === 'APPROVED_SPEC_BOUND' && autonomousStates.has(run.state);\n}\n\nexport function automaticAutonomyOperationKey(run: EngineeringRunContinuationIdentity): string {\n  if (!run.id.trim()) throw new Error('Engineering Run id is required for automatic autonomy.');\n  if (!Number.isInteger(run.revision) || run.revision < 0) throw new Error('Engineering Run revision is invalid for automatic autonomy.');\n  const key = `autonomous-auto-${run.id}-${run.revision}`;\n  if (key.length > 160) throw new Error('Automatic autonomy operation identity is unbounded.');\n  return key;\n}\n\nexport function autonomyContinuationDisposition(\n  run: EngineeringRunContinuationIdentity,\n  stopReason: string,\n  completedRequests: number,\n): AutonomyContinuationDisposition {\n  if (!Number.isInteger(completedRequests) || completedRequests < 1) {\n    throw new Error('Autonomy continuation request count is invalid.');\n  }\n  if (stopReason !== 'MAX_STEPS_REACHED' || !canContinueEngineeringRunAutonomously(run)) {\n    return 'STOP';\n  }\n  return completedRequests >= MAX_AUTONOMY_REQUESTS_PER_CONTINUATION\n    ? 'LIMIT_REACHED'\n    : 'CONTINUE';\n}\n''',
    encoding="utf-8",
)

replace_exact(
    "apps/client/src/hooks/useEngineeringRun.ts",
    '''import {\n  automaticAutonomyOperationKey,\n  canContinueEngineeringRunAutonomously,\n} from '../state/engineeringRunContinuation';\n''',
    '''import {\n  automaticAutonomyOperationKey,\n  autonomyContinuationDisposition,\n  canContinueEngineeringRunAutonomously,\n  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n} from '../state/engineeringRunContinuation';\n''',
)
replace_exact(
    "apps/client/src/hooks/useEngineeringRun.ts",
    '''  const applyAutonomyResult = React.useCallback(async (candidate: EngineeringRunDto, operationKey: string) => {\n    const result = await runEngineeringAutonomy(candidate, operationKey);\n    const next: EngineeringRunView = { ...result.run, autonomy_stop_reason: result.stop_reason };\n    setRun(next);\n    clearFailure();\n    return next;\n  }, [clearFailure]);\n''',
    '''  const applyAutonomyResult = React.useCallback(async (candidate: EngineeringRunDto, operationKey: string) => {\n    let current = candidate;\n    let currentOperationKey = operationKey;\n\n    for (let completedRequests = 1; completedRequests <= MAX_AUTONOMY_REQUESTS_PER_CONTINUATION; completedRequests += 1) {\n      const result = await runEngineeringAutonomy(current, currentOperationKey);\n      const next: EngineeringRunView = { ...result.run, autonomy_stop_reason: result.stop_reason };\n      setRun(next);\n      clearFailure();\n\n      const disposition = autonomyContinuationDisposition(\n        result.run,\n        result.stop_reason,\n        completedRequests,\n      );\n      if (disposition === 'STOP') return next;\n      if (disposition === 'LIMIT_REACHED') {\n        throw new EngineeringAutonomyError(\n          'Parallax paused automatic continuation after eight protected steps. Try again to continue.',\n          'AUTONOMY_CONTINUATION_LIMIT',\n        );\n      }\n\n      current = result.run;\n      currentOperationKey = automaticAutonomyOperationKey(current);\n    }\n\n    throw new EngineeringAutonomyError(\n      'Parallax paused automatic continuation at its protected request limit. Try again to continue.',\n      'AUTONOMY_CONTINUATION_LIMIT',\n    );\n  }, [clearFailure]);\n''',
)
replace_exact(
    "apps/client/src/hooks/useEngineeringRun.ts",
    '''          // One bounded continuation attempt per refresh. The deterministic\n          // key makes StrictMode/reconnect replay safe and prevents duplicate\n          // protected execution for the same server revision.\n''',
    '''          // Continue through finite one-stage requests. Every handoff is\n          // bound to the newly returned server revision, so StrictMode/reconnect\n          // replay cannot duplicate a protected stage transition.\n''',
)

# Extend existing client policy test so it executes in the established state lane.
replace_exact(
    "apps/client/scripts/test-engineering-run-continuation.cjs",
    '''  automaticAutonomyOperationKey,\n  canContinueEngineeringRunAutonomously,\n} = require('../.tmp-state/engineeringRunContinuation.js');\n''',
    '''  automaticAutonomyOperationKey,\n  autonomyContinuationDisposition,\n  canContinueEngineeringRunAutonomously,\n  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n} = require('../.tmp-state/engineeringRunContinuation.js');\n''',
)
replace_exact(
    "apps/client/scripts/test-engineering-run-continuation.cjs",
    '''assert.throws(\n  () => automaticAutonomyOperationKey({ ...base, revision: -1, state: 'PLAN' }),\n  /revision is invalid/,\n);\n\nconsole.log('PASS engineering run continuation policy');\n''',
    '''assert.throws(\n  () => automaticAutonomyOperationKey({ ...base, revision: -1, state: 'PLAN' }),\n  /revision is invalid/,\n);\n\nassert.equal(MAX_AUTONOMY_REQUESTS_PER_CONTINUATION, 8);\nassert.equal(\n  autonomyContinuationDisposition({ ...base, state: 'IMPLEMENT' }, 'MAX_STEPS_REACHED', 1),\n  'CONTINUE',\n);\nassert.equal(\n  autonomyContinuationDisposition(\n    { ...base, state: 'VERIFY' },\n    'MAX_STEPS_REACHED',\n    MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,\n  ),\n  'LIMIT_REACHED',\n);\nassert.equal(\n  autonomyContinuationDisposition({ ...base, state: 'REVIEW' }, 'REVIEW_REQUIRED', 1),\n  'STOP',\n);\nassert.equal(\n  autonomyContinuationDisposition({ ...base, state: 'FAILED' }, 'MAX_STEPS_REACHED', 1),\n  'STOP',\n);\nassert.throws(\n  () => autonomyContinuationDisposition({ ...base, state: 'PLAN' }, 'MAX_STEPS_REACHED', 0),\n  /request count is invalid/,\n);\n\nconsole.log('PASS engineering run continuation policy');\n''',
)

# Existing transport tests now assert the finite production call budget.
replace_exact(
    "services/api/tests/test_dspy_gateway_routing.py",
    '''    assert kwargs == {\n        "api_base": "https://ai-gateway.vercel.sh/v1",\n        "api_key": "request-oidc-secret",\n    }\n''',
    '''    assert kwargs == {\n        "api_base": "https://ai-gateway.vercel.sh/v1",\n        "api_key": "request-oidc-secret",\n        "timeout": 60,\n        "num_retries": 0,\n    }\n''',
)
replace_exact(
    "services/api/tests/test_dspy_gateway_routing.py",
    '''    assert lm.kwargs == {\n        "api_base": "https://ai-gateway.vercel.sh/v1",\n        "api_key": "thread-request-secret",\n    }\n''',
    '''    assert lm.kwargs == {\n        "api_base": "https://ai-gateway.vercel.sh/v1",\n        "api_key": "thread-request-secret",\n        "timeout": 60,\n        "num_retries": 0,\n    }\n''',
)

# Adapt the prior structured-output regression to the typed JSONAdapter contract.
replace_exact(
    "services/api/tests/test_structured_output_classification_v02315.py",
    '''class _FakeDspy:\n    def context(self, **_kwargs):\n        return nullcontext()\n\n\nclass _MalformedPredictionProgram:\n    def __call__(self, **_kwargs):\n        return SimpleNamespace(\n            proposal_json='{\"acceptance_ids_covered\":\"AC-01\",\"patches\":[]}'\n        )\n''',
    '''class _FakeDspy:\n    def __init__(self):\n        self.adapter = object()\n        self.context_kwargs: list[dict[str, object]] = []\n\n    def JSONAdapter(self):  # noqa: N802 - mirrors DSPy API\n        return self.adapter\n\n    def context(self, **kwargs):\n        self.context_kwargs.append(kwargs)\n        return nullcontext()\n\n\nclass _MalformedPredictionProgram:\n    def __call__(self, **_kwargs):\n        return SimpleNamespace(\n            acceptance_ids_covered="AC-01",\n            patches=[],\n        )\n\n\nclass _TypedPredictionProgram:\n    def __init__(self, request: ImplementationGenerationRequest):\n        self.request = request\n\n    def __call__(self, **_kwargs):\n        proposal = _proposal(self.request)\n        return SimpleNamespace(\n            acceptance_ids_covered=proposal.acceptance_ids_covered,\n            patches=[item.model_dump() for item in proposal.patches],\n        )\n''',
)
replace_exact(
    "services/api/tests/test_structured_output_classification_v02315.py",
    '''def test_dspy_program_wraps_pydantic_decode_failure_without_raw_output():\n    program = DspyImplementationGenerationProgram.__new__(DspyImplementationGenerationProgram)\n    program._dspy = _FakeDspy()\n    program._lm = object()\n    program._program = _MalformedPredictionProgram()\n\n    with pytest.raises(ModelOutputValidationError) as captured:\n        program.run(request=_request())\n\n    assert "synthetic" not in str(captured.value)\n    assert "proposal_json" not in str(captured.value)\n    assert "acceptance_ids_covered" not in str(captured.value)\n    assert captured.value.__cause__ is None\n''',
    '''def test_dspy_program_wraps_pydantic_decode_failure_without_raw_output():\n    program = DspyImplementationGenerationProgram.__new__(DspyImplementationGenerationProgram)\n    fake_dspy = _FakeDspy()\n    program._dspy = fake_dspy\n    program._lm = object()\n    program._program = _MalformedPredictionProgram()\n\n    with pytest.raises(ModelOutputValidationError) as captured:\n        program.run(request=_request())\n\n    assert "synthetic" not in str(captured.value)\n    assert "acceptance_ids_covered" not in str(captured.value)\n    assert captured.value.__cause__ is None\n    assert fake_dspy.context_kwargs[-1]["adapter"] is fake_dspy.adapter\n\n\ndef test_dspy_program_uses_typed_json_adapter_output():\n    request = _request()\n    program = DspyImplementationGenerationProgram.__new__(DspyImplementationGenerationProgram)\n    fake_dspy = _FakeDspy()\n    program._dspy = fake_dspy\n    program._lm = object()\n    program._program = _TypedPredictionProgram(request)\n\n    proposal = program.run(request=request)\n\n    assert proposal == _proposal(request)\n    assert fake_dspy.context_kwargs[-1]["adapter"] is fake_dspy.adapter\n''',
)

Path("services/api/tests/test_request_bounded_autonomy_v02322.py").write_text(
    '''from __future__ import annotations\n\nfrom types import SimpleNamespace\n\nimport pytest\n\nfrom parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason\nfrom parallax_api.code.domain import WorkflowStage\nfrom parallax_api.code.execution import ExecutionSpec\nimport parallax_api.code.agentic_candidate_recovery as candidate_recovery\nimport parallax_api.routes.engineering_runs as engineering_routes\nfrom parallax_api.schemas import EngineeringOperation\n\n\nclass _OneStepService:\n    def __init__(self):\n        self.run = SimpleNamespace(\n            id="run-1",\n            state=WorkflowStage.VERIFY.value,\n            revision=4,\n            attempts=[],\n        )\n        self.completed: list[WorkflowStage] = []\n\n    def get(self, run_id: str):\n        assert run_id == self.run.id\n        return self.run\n\n    def acceptance_map_for_run(self, _run):\n        return [{"id": "AC-01"}]\n\n    def complete_stage(self, *, stage: WorkflowStage, **_kwargs):\n        self.completed.append(stage)\n        self.run.state = WorkflowStage.REVIEW.value\n        self.run.revision += 1\n        return SimpleNamespace(run=self.run, attempt_id="attempt-verify", replayed=False)\n\n\nclass _Executor:\n    def probe(self, *, operation_key: str):\n        raise AssertionError(operation_key)\n\n    def execute(self, spec: ExecutionSpec):\n        return {"tool_id": spec.tool_id, "protected_success": True}\n\n\nclass _Registry:\n    def spec_for(self, stage: WorkflowStage, *, operation_key: str):\n        return ExecutionSpec(\n            tool_id="verify",\n            args=(),\n            working_directory=".",\n            timeout_seconds=1,\n            environment_names=(),\n            stage=stage,\n            operation_key=operation_key,\n        )\n\n\ndef test_one_step_verify_returns_review_boundary_instead_of_max_steps():\n    service = _OneStepService()\n    result = AutonomyCoordinator(\n        service,\n        _Executor(),\n        registry=_Registry(),\n        max_steps=1,\n    ).run(\n        run_id="run-1",\n        operation_key="p2322-one-step",\n        expected_revision=4,\n    )\n\n    assert service.completed == [WorkflowStage.VERIFY]\n    assert result.run.state == WorkflowStage.REVIEW.value\n    assert result.stop_reason is AutonomyStopReason.REVIEW_REQUIRED\n    assert [step.stage for step in result.steps] == [WorkflowStage.VERIFY.value]\n\n\nclass _RouteService:\n    owner_subject = "owner-a"\n\n    def __init__(self):\n        self.runs = SimpleNamespace(session=object())\n        self.run = SimpleNamespace(id="run-route", project_id="project-route")\n\n    def get(self, run_id: str):\n        assert run_id == self.run.id\n        return self.run\n\n\nclass _RouteRuntime:\n    def __init__(self, captured: dict[str, object]):\n        self.captured = captured\n\n    def run(self, *, run_id: str, operation_key: str, expected_revision: int):\n        self.captured["run"] = (run_id, operation_key, expected_revision)\n        return SimpleNamespace(\n            run=SimpleNamespace(id=run_id),\n            stop_reason=AutonomyStopReason.MAX_STEPS_REACHED,\n            steps=(),\n        )\n\n\ndef test_production_agentic_route_pins_one_lifecycle_stage(monkeypatch: pytest.MonkeyPatch):\n    captured: dict[str, object] = {}\n    service = _RouteService()\n    runtime = _RouteRuntime(captured)\n\n    monkeypatch.setenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", "1")\n    monkeypatch.setattr(engineering_routes, "production_source_delivery", lambda *_args, **_kwargs: object())\n    monkeypatch.setattr(engineering_routes, "present", lambda run, _svc: {"id": run.id})\n\n    def build_runtime(*_args, **kwargs):\n        captured["max_steps"] = kwargs.get("max_steps")\n        return runtime\n\n    monkeypatch.setattr(candidate_recovery, "build_resilient_live_agentic_runtime_composition", build_runtime)\n\n    response = engineering_routes.autonomous(\n        "run-route",\n        EngineeringOperation(operation_key="p2322-route", expected_revision=9),\n        svc=service,\n        allocator=object(),\n        oidc_token="oidc",\n    )\n\n    assert captured["max_steps"] == 1\n    assert captured["run"] == ("run-route", "p2322-route", 9)\n    assert response["stop_reason"] == AutonomyStopReason.MAX_STEPS_REACHED.value\n\n\ndef test_production_nonagentic_route_pins_one_lifecycle_stage(monkeypatch: pytest.MonkeyPatch):\n    captured: dict[str, object] = {}\n    service = _RouteService()\n    runtime = _RouteRuntime(captured)\n\n    monkeypatch.delenv("PARALLAX_AGENTIC_RUNTIME_ENABLED", raising=False)\n    monkeypatch.setattr(engineering_routes, "production_source_delivery", lambda *_args, **_kwargs: object())\n    monkeypatch.setattr(engineering_routes, "present", lambda run, _svc: {"id": run.id})\n\n    class RuntimeFactory:\n        def __init__(self, *_args, **kwargs):\n            captured["max_steps"] = kwargs.get("max_steps")\n\n        def run(self, **kwargs):\n            return runtime.run(**kwargs)\n\n    monkeypatch.setattr(engineering_routes, "EngineeringRuntimeComposition", RuntimeFactory)\n\n    response = engineering_routes.autonomous(\n        "run-route",\n        EngineeringOperation(operation_key="p2322-route-nonagentic", expected_revision=11),\n        svc=service,\n        allocator=object(),\n        oidc_token="oidc",\n    )\n\n    assert captured["max_steps"] == 1\n    assert captured["run"] == ("run-route", "p2322-route-nonagentic", 11)\n    assert response["stop_reason"] == AutonomyStopReason.MAX_STEPS_REACHED.value\n''',
    encoding="utf-8",
)

print("P2-V0.23.22 implementation patch applied")
