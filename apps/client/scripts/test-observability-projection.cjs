const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const {
  activeRunObservation,
  componentHealth,
  evidenceAuditFacts,
  observabilitySummary,
  providerIdentities,
  recentAlerts,
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
  dashboardCompositionContract: true,
  fabricatedTelemetryAbsent: true,
}, null, 2));
