const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const {
  activeRunObservation,
  componentHealth,
  evidenceAuditFacts,
  observabilitySummary,
  providerIdentities,
  projectPipeline,
  recentAlerts,
  safeEventMetadata,
} = require('../.tmp-observability/lib/observabilityProjection.js');

const PROJECT_ID = '77777777-7777-4777-8777-777777777777';
const RUN_ID = '44444444-4444-4444-8444-444444444444';
const PARENT = `src:${'a'.repeat(64)}`;
const CANDIDATE = `src:${'b'.repeat(64)}`;

function event(sequence, overrides = {}) {
  return {
    id: `10000000-0000-4000-8000-${String(sequence).padStart(12, '0')}`,
    project_id: PROJECT_ID,
    run_id: RUN_ID,
    sequence,
    event_key: `projection-${sequence}`,
    event_type: 'STAGE_RESULT',
    stage: null,
    outcome: 'INFO',
    subsystem: 'RUN',
    attempt_id: null,
    worker_execution_id: null,
    source_lineage_ref: null,
    parent_source_lineage_ref: null,
    operation_ref: null,
    artifact_ref: null,
    evidence_ref: null,
    failure_code: null,
    summary: `event ${sequence}`,
    metadata: {},
    occurred_at: '2026-08-25T01:00:00Z',
    created_at: '2026-08-25T01:00:00Z',
    ...overrides,
  };
}

const failedRun = {
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
assert.equal(emptySummary.find((item) => item.key === 'sequence').value, 'Unavailable');
assert.equal(emptySummary.find((item) => item.key === 'attention').value, 'Not measured');
assert.equal(componentHealth([], 'CLOSED').find((item) => item.key === 'github').status, 'Unavailable');
assert.equal(evidenceAuditFacts([]).find((item) => item.key === 'project').value, 'Unavailable');

const events = [
  event(1, { event_type: 'RUN_CREATED', outcome: 'STARTED', summary: 'Run created.' }),
  event(2, { event_type: 'SOURCE_LINEAGE_ACCEPTED', stage: 'IMPLEMENT', outcome: 'SUCCEEDED', subsystem: 'SOURCE_LINEAGE', source_lineage_ref: CANDIDATE, parent_source_lineage_ref: PARENT, summary: 'Candidate accepted.' }),
  event(3, { event_type: 'WORKER_STATE', outcome: 'RECOVERING', subsystem: 'WORKER', worker_execution_id: 'worker:one', summary: 'Recovering from process loss.' }),
  event(4, { stage: 'TEST', outcome: 'FAILED', subsystem: 'EXECUTION', attempt_id: '55555555-5555-4555-8555-555555555555', evidence_ref: 'evidence:test:1', failure_code: 'TEST_FAILURE', summary: 'Tests failed.' }),
  event(5, { event_type: 'PROVIDER_RESULT', outcome: 'SUCCEEDED', subsystem: 'GITHUB', metadata: { pull_request_number: 172 }, summary: 'Pull request created.' }),
  event(6, { event_type: 'PROVIDER_RESULT', outcome: 'SUCCEEDED', subsystem: 'VERCEL', metadata: { preview_deployment_id: 'preview-172', preview_status: 'READY' }, summary: 'Preview ready.' }),
  event(7, { event_type: 'REVIEW_REQUIRED', stage: 'REVIEW', outcome: 'HUMAN_REQUIRED', subsystem: 'REVIEW', summary: 'Operator review required.' }),
];

const summary = observabilitySummary(events);
assert.equal(summary.find((item) => item.key === 'events').value, '7');
assert.equal(summary.find((item) => item.key === 'sequence').value, '#7');
assert.equal(summary.find((item) => item.key === 'attention').value, '3');
assert.equal(summary.find((item) => item.key === 'recovery').value, '1');

const health = componentHealth(events, 'LIVE');
assert.equal(health.find((item) => item.key === 'event-plane').status, 'Live');
assert.equal(health.find((item) => item.key === 'worker').status, 'Recovering');
assert.equal(health.find((item) => item.key === 'source-lineage').status, 'Observed');
assert.equal(health.find((item) => item.key === 'github').status, 'Observed');
assert.equal(health.find((item) => item.key === 'vercel').status, 'Observed');
assert.equal(health.find((item) => item.key === 'evaluation').status, 'Unavailable');

const resumedEvents = [
  event(10, { event_type: 'SOURCE_LINEAGE_ACCEPTED', stage: 'IMPLEMENT', outcome: 'SUCCEEDED', subsystem: 'SOURCE_LINEAGE', source_lineage_ref: CANDIDATE, parent_source_lineage_ref: PARENT, summary: 'Candidate lineage persisted.' }),
  event(11, { event_type: 'WORKER_STATE', stage: 'IMPLEMENT', outcome: 'FAILED', subsystem: 'WORKER', worker_execution_id: 'worker:failed', source_lineage_ref: CANDIDATE, failure_code: 'AGENTIC_CANDIDATE_EXHAUSTED', summary: 'Protected worker stall classification produced FAILED state.' }),
  event(12, { event_type: 'STAGE_RESULT', stage: 'IMPLEMENT', outcome: 'FAILED', subsystem: 'IMPLEMENTATION', failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED', summary: 'Protected IMPLEMENT attempt recorded as FAILED.' }),
  event(13, { event_type: 'RUN_CONTROL', stage: 'IMPLEMENT', outcome: 'PROGRESSED', subsystem: 'IMPLEMENTATION', summary: 'Engineering Run control recorded as RESUMED.', metadata: { control_status: 'RESUMED' } }),
];
const resumedRun = { state: 'IMPLEMENT', resume_stage: 'IMPLEMENT', last_failure_code: null };
const resumedHealth = componentHealth(resumedEvents, 'LIVE', resumedRun);
const resumedWorker = resumedHealth.find((item) => item.key === 'worker');
const resumedLineage = resumedHealth.find((item) => item.key === 'source-lineage');
assert.equal(resumedWorker.status, 'Awaiting evidence');
assert.equal(resumedWorker.tone, 'teal');
assert.equal(resumedWorker.sequence, 13);
assert.equal(resumedWorker.detail.includes('prior component failure #11'), true);
assert.equal(resumedLineage.status, 'Observed');
assert.equal(resumedLineage.tone, 'olive');
assert.equal(resumedLineage.sequence, 10);
assert.equal(resumedLineage.detail, 'Candidate lineage persisted.');

const referencedOnlyEvents = [
  event(20, { event_type: 'STAGE_RESULT', stage: 'IMPLEMENT', outcome: 'FAILED', subsystem: 'IMPLEMENTATION', worker_execution_id: 'worker:referenced', source_lineage_ref: CANDIDATE, failure_code: 'IMPLEMENT_FAILED', summary: 'Implementation failed for a reason outside component health.' }),
];
const referencedOnlyHealth = componentHealth(referencedOnlyEvents, 'LIVE', { state: 'IMPLEMENT', resume_stage: 'IMPLEMENT', last_failure_code: null });
assert.equal(referencedOnlyHealth.find((item) => item.key === 'worker').status, 'Observed');
assert.equal(referencedOnlyHealth.find((item) => item.key === 'worker').tone, 'teal');
assert.equal(referencedOnlyHealth.find((item) => item.key === 'source-lineage').status, 'Observed');
assert.equal(referencedOnlyHealth.find((item) => item.key === 'source-lineage').tone, 'teal');

const audit = evidenceAuditFacts(events);
assert.equal(audit.find((item) => item.key === 'project').value, PROJECT_ID);
assert.equal(audit.find((item) => item.key === 'run').value, RUN_ID);
assert.equal(audit.find((item) => item.key === 'candidate').value, CANDIDATE);
assert.equal(audit.find((item) => item.key === 'parent').value, PARENT);
assert.equal(audit.find((item) => item.key === 'evidence').value, 'evidence:test:1');
assert.equal(audit.find((item) => item.key === 'artifact').value, 'Unavailable');

const providers = providerIdentities(events);
assert.equal(providers[0].provider, 'Vercel');
assert.equal(providers[0].identifier, 'preview-172');
assert.equal(providers[1].provider, 'GitHub');
assert.equal(providers[1].identifier, 'PR #172');

const alerts = recentAlerts(events);
assert.equal(alerts[0].title, 'Human review required');
assert.equal(alerts.some((item) => item.detail === 'Recovering from process loss.'), true);

const active = activeRunObservation(events);
assert.equal(active.projectId, PROJECT_ID);
assert.equal(active.runId, RUN_ID);
assert.equal(active.latestStage, 'REVIEW');
assert.equal(active.latestOutcome, 'HUMAN_REQUIRED');
assert.equal(active.latestSequence, '#7');

const liveBuildSource = readFileSync('src/components/observability/LiveBuildWorkspace.tsx', 'utf8');
for (const required of [
  'live-build-durable-failure',
  'Durable run failure',
  'Missing optional worker, provider, preview, lineage, or evaluation evidence does not mean the run is still waiting.',
]) {
  assert.equal(liveBuildSource.includes(required), true, `Missing durable failure fallback marker: ${required}`);
}

const dashboardSource = readFileSync('src/components/observability/RunEventStream.tsx', 'utf8');
for (const required of [
  'observability-summary-strip',
  'Run Event Stream',
  'Component Health',
  'Evidence &amp; Audit',
  'Missing evidence stays unavailable',
  'Provider actions remain unavailable unless an accepted URL is explicitly present in evidence',
  'Observation is paused locally. Run execution and persisted event capture are unchanged.',
]) {
  assert.equal(dashboardSource.includes(required), true, `Missing Observability contract marker: ${required}`);
}
for (const forbidden of ['Average latency', 'Token usage', 'Queue depth', 'Provider SLA']) {
  assert.equal(dashboardSource.includes(forbidden), false, `Fabricated telemetry surface is forbidden: ${forbidden}`);
}

console.log(JSON.stringify({
  truthfulEmptyStates: true,
  runScopedSummary: true,
  componentHealthEvidenceOnly: true,
  durableAuditFacts: true,
  providerIdentityEvidenceOnly: true,
  recoveryAndHumanRequiredDistinct: true,
  durableFailureFallback: true,
  dashboardCompositionContract: true,
  fabricatedTelemetryAbsent: true,
}, null, 2));
