import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.css': 'text/css; charset=utf-8',
};

const PROJECT_ID = '77777777-7777-4777-8777-777777777777';
const CONVERSATION_ID = '33333333-3333-4333-8333-333333333333';
const SPEC_ID = '22222222-2222-4222-8222-222222222222';
const RUN_ID = '44444444-4444-4444-8444-444444444444';
const CANDIDATE = `src:${'b'.repeat(64)}`;
const PARENT = `src:${'a'.repeat(64)}`;
const now = '2026-08-30T03:44:42Z';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

const conversation = {
  id: CONVERSATION_ID,
  title: 'Resumed protected implementation',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.23.9',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: now,
  updated_at: now,
  messages: [{ id: 'm1', role: 'assistant', content: 'Protected implementation remains active.', status: 'complete', created_at: now }],
};

const workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Resumed protected implementation',
  objective: 'Continue the approved implementation safely.',
  constraints: ['Preserve protected execution boundaries.'],
  acceptance_criteria: ['Keep current health distinct from immutable historical failures.'],
  risks: ['Historical failure evidence must remain visible.'],
  open_questions: [],
  confidence: 0.98,
  program_version: 'work-spec-v0.23.9',
  model_id: 'resumed-component-health-smoke',
  created_at: now,
  updated_at: now,
  approved_at: now,
};

const engineeringRun = {
  id: RUN_ID,
  conversation_id: CONVERSATION_ID,
  spec_id: 'P2-V0.23.9',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  work_specification_id: SPEC_ID,
  work_specification_revision: 1,
  work_specification_digest: 'c'.repeat(64),
  binding_status: 'APPROVED_SPEC_BOUND',
  acceptance_criteria: [{ id: 'AC-01', text: workSpecification.acceptance_criteria[0] }],
  state: 'IMPLEMENT',
  resume_stage: 'IMPLEMENT',
  revision: 3,
  workspace_ref: null,
  last_failure_code: null,
  completed_at: null,
  created_at: now,
  updated_at: now,
  attempts: [
    { id: '11111111-1111-4111-8111-111111111111', stage: 'IMPLEMENT', attempt_number: 1, status: 'FAILED', failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED', evidence: {}, started_at: now, completed_at: now },
    { id: '22222222-1111-4111-8111-111111111111', stage: 'IMPLEMENT', attempt_number: 3, status: 'FAILED', failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED', evidence: {}, started_at: now, completed_at: now },
  ],
};

const failedEngineeringRun = {
  ...engineeringRun,
  state: 'FAILED',
  resume_stage: 'IMPLEMENT',
  revision: 3,
  last_failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED',
};

const resumedEngineeringRun = {
  ...engineeringRun,
  state: 'IMPLEMENT',
  resume_stage: 'IMPLEMENT',
  revision: 4,
  last_failure_code: null,
};

const continuedEngineeringRun = {
  ...engineeringRun,
  state: 'REVIEW',
  resume_stage: null,
  revision: 5,
  last_failure_code: null,
};

let latestEngineeringRun = engineeringRun;
let resumeContinuationScenario = false;
const continuationCalls = [];

function event(sequence, overrides = {}) {
  return {
    id: `10000000-0000-4000-8000-${String(sequence).padStart(12, '0')}`,
    project_id: PROJECT_ID,
    run_id: RUN_ID,
    sequence,
    event_key: `resume-regression-${sequence}`,
    event_type: 'STAGE_RESULT',
    stage: 'IMPLEMENT',
    outcome: 'INFO',
    subsystem: 'IMPLEMENTATION',
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
    occurred_at: now,
    created_at: now,
    ...overrides,
  };
}

const events = [
  event(10, {
    event_type: 'SOURCE_LINEAGE_ACCEPTED',
    outcome: 'SUCCEEDED',
    subsystem: 'SOURCE_LINEAGE',
    source_lineage_ref: CANDIDATE,
    parent_source_lineage_ref: PARENT,
    summary: 'Candidate lineage persisted.',
  }),
  event(11, {
    event_type: 'WORKER_STATE',
    outcome: 'FAILED',
    subsystem: 'WORKER',
    worker_execution_id: 'worker:failed',
    source_lineage_ref: CANDIDATE,
    failure_code: 'AGENTIC_CANDIDATE_EXHAUSTED',
    summary: 'Protected worker stall classification produced FAILED state.',
    metadata: { retry_count: 0 },
  }),
  event(12, {
    outcome: 'FAILED',
    failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED',
    summary: 'Protected IMPLEMENT attempt recorded as FAILED.',
    metadata: { attempt_number: 1 },
  }),
  event(13, {
    event_type: 'RUN_CONTROL',
    outcome: 'PROGRESSED',
    summary: 'Engineering Run control recorded as RESUMED.',
    metadata: { control_status: 'RESUMED', attempt_number: 2 },
  }),
  event(14, {
    outcome: 'FAILED',
    failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED',
    summary: 'Protected IMPLEMENT attempt recorded as FAILED.',
    metadata: { attempt_number: 3 },
  }),
];

function cors(response, origin) {
  response.setHeader('access-control-allow-origin', origin ?? '*');
  response.setHeader('access-control-allow-credentials', 'true');
  response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Last-Event-ID,Authorization');
  response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
}

function json(response, status, payload, origin) {
  cors(response, origin);
  response.writeHead(status, { 'content-type': 'application/json' });
  response.end(JSON.stringify(payload));
}

const streamResponses = new Set();

function apiServer() {
  return createServer((request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') {
      cors(response, origin);
      response.writeHead(204);
      response.end();
      return;
    }

    const url = new URL(request.url ?? '/', 'http://localhost');
    const pathname = url.pathname;

    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, latestEngineeringRun, origin);
    if (pathname === `/v1/engineering-runs/${RUN_ID}/resume` && request.method === 'POST') {
      if (!resumeContinuationScenario) return json(response, 409, { detail: 'resume scenario not active' }, origin);
      continuationCalls.push('resume');
      latestEngineeringRun = resumedEngineeringRun;
      return json(response, 200, { run: resumedEngineeringRun, attempt_id: null, replayed: false }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/autonomous` && request.method === 'POST') {
      if (resumeContinuationScenario) {
        continuationCalls.push('autonomous');
        latestEngineeringRun = continuedEngineeringRun;
        return json(response, 200, { run: continuedEngineeringRun, stop_reason: 'REVIEW_REQUIRED', steps: [] }, origin);
      }
      return json(response, 200, { run: engineeringRun, stop_reason: 'FAILED', steps: [] }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events` && request.method === 'GET') {
      const after = Number(url.searchParams.get('after_sequence') ?? '0');
      const page = events.filter((item) => item.sequence > after);
      return json(response, 200, { events: page, next_after_sequence: page.at(-1)?.sequence ?? after, has_more: false }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events/stream` && request.method === 'GET') {
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      response.write(': connected\n\n');
      streamResponses.add(response);
      request.on('close', () => streamResponses.delete(response));
      return;
    }

    return json(response, 404, { detail: 'not found' }, origin);
  });
}

function staticServer() {
  return createServer((request, response) => {
    const rawPath = new URL(request.url ?? '/', 'http://localhost').pathname;
    const relative = rawPath === '/' ? 'index.html' : rawPath.replace(/^\/+/, '');
    const target = normalize(join(root, relative));
    if (!target.startsWith(normalize(root)) || !existsSync(target)) {
      response.writeHead(404, { 'content-type': 'text/plain' });
      response.end('not found');
      return;
    }
    response.writeHead(200, {
      'content-type': mime[extname(target)] ?? 'application/octet-stream',
      'cache-control': 'no-store',
    });
    createReadStream(target).pipe(response);
  });
}

const web = staticServer();
const api = apiServer();
let browser;
try {
  await Promise.all([listen(web, 8774), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('http://127.0.0.1:8774', { waitUntil: 'domcontentloaded' });

  await mobile.getByRole('tab', { name: 'Progress', exact: true }).click();
  await mobile.getByTestId('mobile-build-workspace').waitFor({ timeout: 8000 });
  await mobile.getByRole('button', { name: 'Open technical build details', exact: true }).click();
  await mobile.getByText('Run observability', { exact: true }).waitFor({ timeout: 8000 });

  await mobile.getByRole('tab', { name: 'Activity', exact: true }).click();
  await mobile.getByTestId('run-event-11').getByText('AGENTIC_CANDIDATE_EXHAUSTED', { exact: true }).waitFor();
  await mobile.getByTestId('run-event-12').getByText('AUTONOMOUS_IMPLEMENT_FAILED', { exact: true }).waitFor();
  await mobile.getByTestId('run-event-13').getByText('Engineering Run control recorded as RESUMED.', { exact: true }).waitFor();
  await mobile.getByTestId('run-event-14').getByText('AUTONOMOUS_IMPLEMENT_FAILED', { exact: true }).waitFor();

  // Component Health is intentionally part of the Activity narrative, exactly as
  // it appears in the operator view. Keep the regression on that same surface
  // rather than switching to the separate compact Health/context section.
  const health = mobile.getByTestId('observability-component-health');
  await health.scrollIntoViewIfNeeded();
  await health.getByText('Component Health', { exact: true }).waitFor();
  await health.getByText('Awaiting evidence', { exact: true }).waitFor();
  await health.getByText('Run control resumed after prior component failure #11; awaiting fresh component evidence.', { exact: true }).waitFor();
  await health.getByText('Candidate lineage persisted.', { exact: true }).waitFor();
  assert(await health.getByText('Attention', { exact: true }).count() === 0, 'Historical worker failure must not remain current Attention after persisted resume');

  // Reproduce the production failure that occurred after the health-projection
  // fix: the server persisted FAILED, the operator chose Try again, /resume
  // returned IMPLEMENT, but the old client stopped there and never called the
  // autonomous endpoint for the newly resumed revision.
  resumeContinuationScenario = true;
  latestEngineeringRun = failedEngineeringRun;
  continuationCalls.length = 0;

  const recovery = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await recovery.goto('http://127.0.0.1:8774', { waitUntil: 'domcontentloaded' });
  await recovery.getByRole('tab', { name: 'Progress', exact: true }).click();
  await recovery.getByRole('button', { name: 'Try again', exact: true }).waitFor({ timeout: 8000 });
  await recovery.getByRole('button', { name: 'Try again', exact: true }).click();
  await recovery.getByText('Ready for your review', { exact: true }).waitFor({ timeout: 8000 });

  const deadline = Date.now() + 8000;
  while (continuationCalls.length < 2 && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  assert(
    continuationCalls.join(',') === 'resume,autonomous',
    `Try again must persist RESUMED then immediately continue autonomously; observed ${continuationCalls.join(',') || 'no calls'}`,
  );

  console.log(JSON.stringify({
    observedSequence: [11, 12, 13, 14],
    activitySurfaceMatched: true,
    workerHealth: 'Awaiting evidence',
    sourceLineage: 'Observed',
    historicalFailurePreserved: true,
    staleCurrentAttentionRejected: true,
    failedResumeAutonomyHandoff: continuationCalls,
    resumedRevision: resumedEngineeringRun.revision,
    continuedRevision: continuedEngineeringRun.revision,
  }, null, 2));
} finally {
  for (const response of streamResponses) response.end();
  if (browser) await browser.close();
  await Promise.all([
    new Promise((resolve) => web.close(resolve)),
    new Promise((resolve) => api.close(resolve)),
  ]);
}
