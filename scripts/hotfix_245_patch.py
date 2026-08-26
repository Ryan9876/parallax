from pathlib import Path


def must_replace(text: str, old: str, new: str, *, count: int = 1) -> str:
    if old not in text:
        raise AssertionError(f"missing patch needle: {old[:120]!r}")
    return text.replace(old, new, count)


path = Path("services/api/parallax_api/code/run_events.py")
text = path.read_text(encoding="utf-8")
text = must_replace(
    text,
    '        "meaningful_progress",\n        "next_recovery_action",\n',
    '        "meaningful_progress",\n        "mutation_applied",\n        "next_recovery_action",\n',
)
path.write_text(text, encoding="utf-8")

path = Path("services/api/parallax_api/code/autonomy.py")
text = path.read_text(encoding="utf-8")
text = must_replace(
    text,
    "from .domain import WorkflowStage\n",
    "from .domain import AttemptStatus, WorkflowStage\n",
)
if "from .run_events import RunEventError\n" not in text:
    text = must_replace(
        text,
        "from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime\n",
        "from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime\nfrom .run_events import RunEventError\n",
    )
old = '''                    failed = self.service.complete_stage(
                        run_id=run.id,
                        stage=WorkflowStage.IMPLEMENT,
                        operation_key=stage_key,
                        expected_revision=run.revision,
                        passed=False,
                        evidence={
                            "error_class": type(exc).__name__,
                            "mutation_applied": False,
                        },
                        failure_code="AUTONOMOUS_IMPLEMENT_FAILED",
                        program_id="protected-implementation-runtime-v0.15.4",
                        tool_id="safe-source-implementation-v1",
                    )
                    steps.append(
                        AutonomyStep(
                            stage=stage.value,
                            outcome="FAILED",
                            attempt_id=failed.attempt_id,
                            replayed=failed.replayed,
                            tool_id="implementation-runtime",
                        )
                    )
                    return AutonomyResult(
                        run=failed.run,
                        stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,
                        steps=tuple(steps),
                    )
'''
new = '''                    try:
                        failed = self.service.complete_stage(
                            run_id=run.id,
                            stage=WorkflowStage.IMPLEMENT,
                            operation_key=stage_key,
                            expected_revision=run.revision,
                            passed=False,
                            evidence={
                                "error_class": type(exc).__name__,
                                "mutation_applied": False,
                            },
                            failure_code="AUTONOMOUS_IMPLEMENT_FAILED",
                            program_id="protected-implementation-runtime-v0.15.4",
                            tool_id="safe-source-implementation-v1",
                        )
                    except RunEventError:
                        # EngineeringRun/attempt persistence commits before optional
                        # observation projection. Recover only the exact expected
                        # durable failure; never fabricate an unknown mutation.
                        recorded = self.service.runs.find_operation(run.id, stage_key)
                        durable_run = self.service.get(run.id)
                        if (
                            recorded is None
                            or recorded.stage != WorkflowStage.IMPLEMENT.value
                            or recorded.status != AttemptStatus.FAILED.value
                            or recorded.failure_code != "AUTONOMOUS_IMPLEMENT_FAILED"
                            or durable_run.state != WorkflowStage.FAILED.value
                            or durable_run.resume_stage != WorkflowStage.IMPLEMENT.value
                            or durable_run.last_failure_code != "AUTONOMOUS_IMPLEMENT_FAILED"
                        ):
                            raise
                        steps.append(
                            AutonomyStep(
                                stage=stage.value,
                                outcome="FAILED",
                                attempt_id=recorded.id,
                                replayed=False,
                                tool_id="implementation-runtime",
                            )
                        )
                        return AutonomyResult(
                            run=durable_run,
                            stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,
                            steps=tuple(steps),
                        )
                    steps.append(
                        AutonomyStep(
                            stage=stage.value,
                            outcome="FAILED",
                            attempt_id=failed.attempt_id,
                            replayed=failed.replayed,
                            tool_id="implementation-runtime",
                        )
                    )
                    return AutonomyResult(
                        run=failed.run,
                        stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,
                        steps=tuple(steps),
                    )
'''
text = must_replace(text, old, new)
path.write_text(text, encoding="utf-8")

path = Path("apps/client/src/lib/observabilityProjection.ts")
text = path.read_text(encoding="utf-8")
text = must_replace(
    text,
    "  key: 'event-plane' | 'worker' | 'source-lineage' | 'github' | 'vercel' | 'evaluation';",
    "  key: 'run' | 'event-plane' | 'worker' | 'source-lineage' | 'github' | 'vercel' | 'evaluation';",
)
text = must_replace(
    text,
    "  'current_step',\n  'evaluation_id',",
    "  'current_step',\n  'error_class',\n  'evaluation_id',",
)
text = must_replace(
    text,
    "  'meaningful_progress',\n  'next_recovery_action',",
    "  'meaningful_progress',\n  'mutation_applied',\n  'next_recovery_action',",
)
text = must_replace(
    text,
    "  return PIPELINE_STAGES.map((stage) => {\n",
    """  const failedStage = run.state === 'FAILED' && run.resume_stage && PIPELINE_STAGES.includes(run.resume_stage as PipelineStage)
    ? run.resume_stage as PipelineStage
    : null;

  return PIPELINE_STAGES.map((stage) => {
""",
)
text = must_replace(
    text,
    """    if (event) {
      return { stage, status: statusForEvent(event), sequence: event.sequence, summary: event.summary };
    }
    // Existing authoritative run state may identify the currently active protected stage,
""",
    """    if (event) {
      return { stage, status: statusForEvent(event), sequence: event.sequence, summary: event.summary };
    }
    if (failedStage === stage) {
      return {
        stage,
        status: 'FAILED',
        sequence: null,
        summary: run.last_failure_code ? `${stage} failed · ${run.last_failure_code}` : `${stage} failed`,
      };
    }
    // Existing authoritative run state may identify the currently active protected stage,
""",
)
text = must_replace(
    text,
    "export function componentHealth(events: RunEventDto[], transport: RunTransportState): ComponentHealthItem[] {\n",
    "export function componentHealth(events: RunEventDto[], transport: RunTransportState, run?: EngineeringRunDto): ComponentHealthItem[] {\n",
)
text = must_replace(
    text,
    "  const worker = latestMatching(events, (event) => event.subsystem === 'WORKER' || Boolean(event.worker_execution_id));\n",
    """  const authoritativeRun: ComponentHealthItem | null = run
    ? run.state === 'FAILED'
      ? {
          key: 'run',
          label: 'Engineering Run',
          status: 'Failed',
          detail: `${run.resume_stage || 'Run'} failed${run.last_failure_code ? ` · ${run.last_failure_code}` : ''}. Durable Engineering Run state remains authoritative even when optional component evidence is unavailable.`,
          sequence: null,
          tone: 'rust',
        }
      : run.state === 'REVIEW'
        ? { key: 'run', label: 'Engineering Run', status: 'Review required', detail: 'Authoritative run reached the protected operator review boundary.', sequence: null, tone: 'olive' }
        : run.state === 'COMPLETE'
          ? { key: 'run', label: 'Engineering Run', status: 'Complete', detail: 'Authoritative run is complete.', sequence: null, tone: 'olive' }
          : { key: 'run', label: 'Engineering Run', status: 'Active', detail: `Authoritative run state: ${run.state}.`, sequence: null, tone: 'teal' }
    : null;

  const worker = latestMatching(events, (event) => event.subsystem === 'WORKER' || Boolean(event.worker_execution_id));
""",
)
text = must_replace(
    text,
    """  return [
    transportItem,
""",
    """  return [
    ...(authoritativeRun ? [authoritativeRun] : []),
    transportItem,
""",
)
path.write_text(text, encoding="utf-8")

path = Path("apps/client/src/components/observability/RunEventStream.tsx")
text = path.read_text(encoding="utf-8")
if "import type { EngineeringRunDto } from '../../lib/api';\n" not in text:
    text = must_replace(
        text,
        "import React from 'react';\n",
        "import React from 'react';\nimport type { EngineeringRunDto } from '../../lib/api';\n",
    )
text = must_replace(
    text,
    "function ComponentHealth({ events, transport }: { events: RunEventDto[]; transport: RunTransportState }) {\n  const items = componentHealth(events, transport);\n",
    "function ComponentHealth({ events, transport, run }: { events: RunEventDto[]; transport: RunTransportState; run: EngineeringRunDto }) {\n  const items = componentHealth(events, transport, run);\n",
)
text = must_replace(
    text,
    "  events,\n  transport,\n  followLive,",
    "  run,\n  events,\n  transport,\n  followLive,",
)
text = must_replace(
    text,
    "  events: RunEventDto[];\n  transport: RunTransportState;",
    "  run: EngineeringRunDto;\n  events: RunEventDto[];\n  transport: RunTransportState;",
)
text = must_replace(
    text,
    "<ComponentHealth events={events} transport={transport} />",
    "<ComponentHealth events={events} transport={transport} run={run} />",
)
path.write_text(text, encoding="utf-8")

path = Path("apps/client/src/components/observability/LiveBuildWorkspace.tsx")
text = path.read_text(encoding="utf-8")
text = must_replace(
    text,
    """  const alerts = recentAlerts(observer.view.events);
  const last = observer.view.events[observer.view.events.length - 1];
""",
    """  const last = observer.view.events[observer.view.events.length - 1];
  const eventAlerts = recentAlerts(observer.view.events);
  const durableFailureAlert = run.state === 'FAILED'
    && !eventAlerts.some((alert) => Boolean(run.last_failure_code) && alert.detail.includes(run.last_failure_code || ''))
    ? {
        key: 'durable-run-failure',
        sequence: last?.sequence ?? 0,
        tone: 'rust' as const,
        title: 'Durable run failure',
        detail: `${run.resume_stage || 'Run'} failed${run.last_failure_code ? ` · ${run.last_failure_code}` : ''}.`,
      }
    : null;
  const alerts = durableFailureAlert ? [durableFailureAlert, ...eventAlerts].slice(0, 5) : eventAlerts;
""",
)
text = must_replace(
    text,
    """        <View style={styles.factRow}><Text style={styles.factLabel}>PROJECT</Text><Text numberOfLines={1} style={styles.factValue}>{run.project_id || 'Historical unbound'}</Text></View>
""",
    """        <View style={styles.factRow}><Text style={styles.factLabel}>PROJECT</Text><Text numberOfLines={1} style={styles.factValue}>{run.project_id || 'Historical unbound'}</Text></View>
        {run.last_failure_code ? <View style={styles.factRow}><Text style={styles.factLabel}>FAILURE</Text><Text style={[styles.factValue, styles.failureValue]}>{run.resume_stage || 'FAILED'} · {run.last_failure_code}</Text></View> : null}
""",
)
text = must_replace(
    text,
    """      </View>
      <View style={styles.runCardGrid}>
""",
    """      </View>
      {run.state === 'FAILED' ? (
        <View style={styles.runFailure} accessibilityLiveRegion="polite" testID="live-build-durable-failure">
          <Text style={styles.runFailureTitle}>{run.resume_stage || 'Run'} failed</Text>
          <Text style={styles.runFailureCode}>{run.last_failure_code || 'Failure code unavailable'}</Text>
          <Text style={styles.contextNote}>This is authoritative Engineering Run state. Missing optional worker, provider, preview, lineage, or evaluation evidence does not mean the run is still waiting.</Text>
        </View>
      ) : null}
      <View style={styles.runCardGrid}>
""",
)
text = text.replace(
    "<RunEventStream events={observer.view.events}",
    "<RunEventStream run={run} events={observer.view.events}",
)
text = text.replace(
    "<RunEventStream compact events={observer.view.events}",
    "<RunEventStream compact run={run} events={observer.view.events}",
)
text = must_replace(
    text,
    """  runStageStatus: { color: palette.teal700, fontSize: 10, fontWeight: '800', marginTop: 4 },
  runCardGrid:""",
    """  runStageStatus: { color: palette.teal700, fontSize: 10, fontWeight: '800', marginTop: 4 },
  runFailure: { padding: 14, borderRadius: 15, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(196,74,27,0.32)', backgroundColor: palette.rust100 },
  runFailureTitle: { color: palette.rust700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  runFailureCode: { color: palette.rust700, fontSize: 10, lineHeight: 15, fontWeight: '700', marginTop: 3, marginBottom: 5 },
  failureValue: { color: palette.rust700 },
  runCardGrid:""",
)
path.write_text(text, encoding="utf-8")

path = Path("services/api/tests/test_run_event_runtime_integration.py")
text = path.read_text(encoding="utf-8")
text = must_replace(
    text,
    "from parallax_api.code.domain import WorkflowStage\n",
    "from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason\nfrom parallax_api.code.domain import WorkflowStage\nfrom parallax_api.code.implementation_runtime import ImplementationRuntimeError\n",
)
addition = """

class _NeverExecutor:
    def probe(self, *, operation_key: str):
        raise AssertionError(f"unexpected executor probe: {operation_key}")

    def execute(self, spec):
        raise AssertionError(f"unexpected executor execution: {spec}")


class _FailingImplementationRuntime:
    def execute(self, **_kwargs):
        raise ImplementationRuntimeError("sanitized implementation failure", mutation_applied=False)


class _FailingProjectionSink:
    def emit(self, _event):
        raise RunEventPersistenceError("injected optional projection failure")


def test_failed_implement_attempt_projects_sanitized_failure_event(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        repository = RunEventRepository(session)
        sink = PersistentRunEventSink(repository)
        project, _, service, run = activate(session, event_sink=sink)
        _, plan = plan_evidence(service, run)
        planned = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="failure-event:plan",
            expected_revision=run.revision,
            passed=True,
            evidence=plan,
        )
        failed = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.IMPLEMENT,
            operation_key="failure-event:implement",
            expected_revision=planned.run.revision,
            passed=False,
            evidence={"error_class": "ImplementationContractError", "mutation_applied": False},
            failure_code="AUTONOMOUS_IMPLEMENT_FAILED",
            program_id="protected-implementation-runtime-v0.15.4",
            tool_id="safe-source-implementation-v1",
        )

        assert failed.run.state == WorkflowStage.FAILED.value
        assert failed.run.resume_stage == WorkflowStage.IMPLEMENT.value
        assert failed.run.last_failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"
        events = repository.list_for_run(project_id=project.id, run_id=run.id, limit=100)
        projected = next(
            event
            for event in events
            if event.append.stage == WorkflowStage.IMPLEMENT.value
            and event.append.outcome is RunEventOutcome.FAILED
        )
        assert projected.append.event_type is RunEventType.STAGE_RESULT
        assert projected.append.subsystem.value == "IMPLEMENTATION"
        assert projected.append.attempt_id == failed.attempt_id
        assert projected.append.failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"
        assert projected.append.metadata["error_class"] == "ImplementationContractError"
        assert projected.append.metadata["mutation_applied"] is False
        serialized = json.dumps(projected.append.canonical_payload(), sort_keys=True)
        assert "sanitized implementation failure" not in serialized


def test_autonomy_returns_durable_failure_when_optional_event_projection_fails(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        project, _, service, run = activate(session, event_sink=None)
        _, plan = plan_evidence(service, run)
        planned = service.complete_stage(
            run_id=run.id,
            stage=WorkflowStage.PLAN,
            operation_key="projection-failure:plan",
            expected_revision=run.revision,
            passed=True,
            evidence=plan,
        )
        service.event_sink = _FailingProjectionSink()

        result = AutonomyCoordinator(
            service,
            _NeverExecutor(),
            implementation_runtime=_FailingImplementationRuntime(),
        ).run(
            run_id=run.id,
            operation_key="projection-failure",
            expected_revision=planned.run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED
        assert result.run.state == WorkflowStage.FAILED.value
        assert result.run.resume_stage == WorkflowStage.IMPLEMENT.value
        assert result.run.last_failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"
        attempts = [item for item in result.run.attempts if item.stage == WorkflowStage.IMPLEMENT.value]
        assert len(attempts) == 1
        assert attempts[0].status == "FAILED"
        assert result.steps[-1].attempt_id == attempts[0].id
        assert result.steps[-1].outcome == "FAILED"
        assert project.id == result.run.project_id
"""
if "test_failed_implement_attempt_projects_sanitized_failure_event" in text:
    raise AssertionError("failure observability tests already present")
text = text.rstrip() + addition + "\n"
path.write_text(text, encoding="utf-8")

path = Path("apps/client/scripts/test-observability-projection.cjs")
text = path.read_text(encoding="utf-8")
text = must_replace(
    text,
    "  providerIdentities,\n  recentAlerts,\n",
    "  providerIdentities,\n  projectPipeline,\n  recentAlerts,\n  safeEventMetadata,\n",
)
text = must_replace(
    text,
    "const emptySummary = observabilitySummary([]);\n",
    """const failedRun = {
  state: 'FAILED',
  resume_stage: 'IMPLEMENT',
  last_failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED',
};
const sparseFailureEvents = [
  event(1, { event_type: 'RUN_CREATED', outcome: 'STARTED', summary: 'Run created.' }),
  event(2, { stage: 'SPECIFY', outcome: 'SUCCEEDED', summary: 'Specification bound.' }),
  event(3, { stage: 'PLAN', outcome: 'SUCCEEDED', summary: 'Plan accepted.' }),
];
const failedPipeline = projectPipeline(failedRun, sparseFailureEvents);
const implementFailure = failedPipeline.find((item) => item.stage === 'IMPLEMENT');
assert.equal(implementFailure.status, 'FAILED');
assert.equal(implementFailure.summary.includes('AUTONOMOUS_IMPLEMENT_FAILED'), true);
const failedHealth = componentHealth(sparseFailureEvents, 'LIVE', failedRun);
const authoritativeFailure = failedHealth.find((item) => item.key === 'run');
assert.equal(authoritativeFailure.status, 'Failed');
assert.equal(authoritativeFailure.detail.includes('IMPLEMENT failed'), true);
assert.equal(authoritativeFailure.detail.includes('AUTONOMOUS_IMPLEMENT_FAILED'), true);
const safeFailureMetadata = safeEventMetadata(event(4, { metadata: { error_class: 'ImplementationContractError', mutation_applied: false } }));
assert.equal(safeFailureMetadata.some((item) => item.key === 'error_class' && item.value === 'ImplementationContractError'), true);
assert.equal(safeFailureMetadata.some((item) => item.key === 'mutation_applied' && item.value === 'false'), true);

const emptySummary = observabilitySummary([]);
""",
)
text = must_replace(
    text,
    "const dashboardSource = readFileSync('src/components/observability/RunEventStream.tsx', 'utf8');\n",
    """const liveBuildSource = readFileSync('src/components/observability/LiveBuildWorkspace.tsx', 'utf8');
for (const required of [
  'live-build-durable-failure',
  'Durable run failure',
  'Missing optional worker, provider, preview, lineage, or evaluation evidence does not mean the run is still waiting.',
]) {
  assert.equal(liveBuildSource.includes(required), true, `Missing durable failure fallback marker: ${required}`);
}

const dashboardSource = readFileSync('src/components/observability/RunEventStream.tsx', 'utf8');
""",
)
text = must_replace(
    text,
    "  dashboardCompositionContract: true,\n",
    "  durableFailureFallback: true,\n  dashboardCompositionContract: true,\n",
)
path.write_text(text, encoding="utf-8")

path = Path("apps/client/scripts/live-build-smoke.mjs")
text = path.read_text(encoding="utf-8")
marker = """  await mobile.getByLabel('Back to conversation').click();
  await mobile.getByLabel('Message Parallax').waitFor();

  assert(await desktop.locator('[data-testid=\"live-build-workspace\"]').count() === 1, 'Desktop Live Build workspace did not mount exactly once');
"""
replacement = """  await mobile.getByLabel('Back to conversation').click();
  await mobile.getByLabel('Message Parallax').waitFor();

  engineeringRun.state = 'FAILED';
  engineeringRun.resume_stage = 'IMPLEMENT';
  engineeringRun.last_failure_code = 'AUTONOMOUS_IMPLEMENT_FAILED';
  engineeringRun.revision = 3;
  engineeringRun.attempts = [{ id: '77777777-7777-4777-8777-777777777778', stage: 'IMPLEMENT', attempt_number: 1, status: 'FAILED', failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED', evidence: { error_class: 'ImplementationContractError', mutation_applied: false }, started_at: now, completed_at: now }];
  events.splice(3);

  const failedMobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await failedMobile.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await failedMobile.getByLabel('Open Live Build observability').click();
  await failedMobile.getByRole('tab', { name: 'Run', exact: true }).click();
  await failedMobile.getByTestId('live-build-durable-failure').waitFor({ timeout: 8000 });
  await failedMobile.getByText('IMPLEMENT failed', { exact: true }).waitFor();
  await failedMobile.getByText('AUTONOMOUS_IMPLEMENT_FAILED', { exact: true }).waitFor();
  await failedMobile.getByRole('tab', { name: 'Activity', exact: true }).click();
  await failedMobile.getByText('Engineering Run', { exact: true }).waitFor();
  await failedMobile.getByText('Failed', { exact: true }).first().waitFor();
  await failedMobile.getByText(/AUTONOMOUS_IMPLEMENT_FAILED/).first().waitFor();

  assert(await desktop.locator('[data-testid=\"live-build-workspace\"]').count() === 1, 'Desktop Live Build workspace did not mount exactly once');
"""
text = must_replace(text, marker, replacement)
text = must_replace(
    text,
    "    mobileLiveBuildEntryAndReturn: true,\n",
    "    mobileLiveBuildEntryAndReturn: true,\n    durableFailedRunFallback: true,\n",
)
path.write_text(text, encoding="utf-8")
