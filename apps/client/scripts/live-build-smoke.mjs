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
};

const PROJECT_ID = '77777777-7777-4777-8777-777777777777';
const CONVERSATION_ID = '33333333-3333-4333-8333-333333333333';
const SPEC_ID = '22222222-2222-4222-8222-222222222222';
const RUN_ID = '44444444-4444-4444-8444-444444444444';
const BUILD_ATTEMPT = '55555555-5555-4555-8555-555555555555';
const TEST_FAILED_ATTEMPT = '66666666-6666-4666-8666-666666666666';
const TEST_PASSED_ATTEMPT = '99999999-9999-4999-8999-999999999999';
const PARENT = `src:${'a'.repeat(64)}`;
const CANDIDATE = `src:${'b'.repeat(64)}`;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
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

const now = '2026-08-24T22:30:00Z';
const conversation = {
  id: CONVERSATION_ID,
  title: 'Incident Correlation Service',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.17.4',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: now,
  updated_at: now,
  messages: [{ id: 'm1', role: 'assistant', content: 'The protected build is ready for operator review.', status: 'complete', created_at: now }],
};
const workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Incident Correlation Service',
  objective: 'Build the governed incident correlation reference service.',
  constraints: ['Preserve protected execution boundaries.'],
  acceptance_criteria: ['Persist run evidence.', 'Require operator review before completion.'],
  risks: ['Provider publication must remain evidence-backed.'],
  open_questions: [],
  confidence: 0.98,
  program_version: 'work-spec-v0.17.4',
  model_id: 'live-build-smoke',
  created_at: now,
  updated_at: now,
  approved_at: now,
};
const engineeringRun = {
  id: RUN_ID,
  conversation_id: CONVERSATION_ID,
  spec_id: 'P2-V0.17.4',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  work_specification_id: SPEC_ID,
  work_specification_revision: 1,
  work_specification_digest: 'c'.repeat(64),
  binding_status: 'APPROVED_SPEC_BOUND',
  acceptance_criteria: [
    { id: 'AC-01', text: workSpecification.acceptance_criteria[0] },
    { id: 'AC-02', text: workSpecification.acceptance_criteria[1] },
  ],
  state: 'REVIEW',
  resume_stage: null,
  revision: 9,
  workspace_ref: null,
  last_failure_code: null,
  completed_at: null,
  created_at: now,
  updated_at: now,
  attempts: [
    { id: BUILD_ATTEMPT, stage: 'BUILD', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
    { id: TEST_FAILED_ATTEMPT, stage: 'TEST', attempt_number: 1, status: 'FAILED', failure_code: 'TEST_FAILURE', evidence: {}, started_at: now, completed_at: now },
    { id: TEST_PASSED_ATTEMPT, stage: 'TEST', attempt_number: 2, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
  ],
};

function event(sequence, overrides = {}) {
  return {
    id: `10000000-0000-4000-8000-${String(sequence).padStart(12, '0')}`,
    project_id: PROJECT_ID,
    run_id: RUN_ID,
    sequence,
    event_key: `live-build-${sequence}`,
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
    occurred_at: now,
    created_at: now,
    ...overrides,
  };
}

const events = [
  event(1, { event_type: 'RUN_CREATED', outcome: 'STARTED', summary: 'Engineering Run created.' }),
  event(2, { stage: 'SPECIFY', outcome: 'SUCCEEDED', summary: 'Approved specification bound.' }),
  event(3, { stage: 'PLAN', outcome: 'SUCCEEDED', summary: 'Implementation plan accepted.' }),
  event(4, { event_type: 'SOURCE_LINEAGE_ACCEPTED', stage: 'IMPLEMENT', outcome: 'SUCCEEDED', subsystem: 'SOURCE_LINEAGE', source_lineage_ref: CANDIDATE, parent_source_lineage_ref: PARENT, summary: 'Candidate source lineage accepted.' }),
  event(5, { stage: 'BUILD', outcome: 'SUCCEEDED', subsystem: 'EXECUTION', attempt_id: BUILD_ATTEMPT, summary: 'Build passed.' }),
  event(6, { stage: 'TEST', outcome: 'FAILED', subsystem: 'EXECUTION', attempt_id: TEST_FAILED_ATTEMPT, failure_code: 'TEST_FAILURE', summary: 'Two tests failed.' }),
  event(7, { event_type: 'WORKER_STATE', outcome: 'RECOVERING', subsystem: 'WORKER', summary: 'Correction loop started.' }),
  event(8, { stage: 'TEST', outcome: 'SUCCEEDED', subsystem: 'EXECUTION', attempt_id: TEST_PASSED_ATTEMPT, summary: 'Tests passed after correction.' }),
  event(9, { event_type: 'PROVIDER_RESULT', outcome: 'SUCCEEDED', subsystem: 'GITHUB', summary: 'GitHub pull request created.', metadata: { pull_request_number: 165, branch_name: 'wave4-reference' } }),
  event(10, { event_type: 'PROVIDER_RESULT', outcome: 'SUCCEEDED', subsystem: 'VERCEL', summary: 'Vercel Preview ready.', metadata: { preview_deployment_id: 'preview-wave4-165', preview_status: 'READY' } }),
  event(11, { event_type: 'REVIEW_REQUIRED', stage: 'REVIEW', outcome: 'HUMAN_REQUIRED', subsystem: 'REVIEW', summary: 'Operator review required before completion.' }),
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
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, engineeringRun, origin);

    if (pathname === `/v1/engineering-runs/${RUN_ID}/events` && request.method === 'GET') {
      const after = Number(url.searchParams.get('after_sequence') ?? '0');
      const page = events.filter((item) => item.sequence > after);
      return json(response, 200, { events: page, next_after_sequence: page.at(-1)?.sequence ?? after, has_more: false }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events/stream` && request.method === 'GET') {
      const after = Number(request.headers['last-event-id'] ?? '0');
      const page = events.filter((item) => item.sequence > after);
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      for (const item of page) response.write(`id: ${item.sequence}\nevent: run-event\ndata: ${JSON.stringify(item)}\n\n`);
      response.end();
      return;
    }
    const treeMatch = pathname.match(new RegExp(`^/v1/engineering-runs/${RUN_ID}/source/(.+)/tree$`));
    if (treeMatch && request.method === 'GET') {
      const lineage = decodeURIComponent(treeMatch[1]);
      if (![PARENT, CANDIDATE].includes(lineage)) return json(response, 404, { detail: 'protected source reference is unavailable' }, origin);
      return json(response, 200, {
        project_id: PROJECT_ID, run_id: RUN_ID, lineage_id: lineage, parent_lineage_id: lineage === CANDIDATE ? PARENT : null,
        content_digest: lineage.slice(4), source_kind: 'protected', file_count: 1, total_bytes: 92,
        files: [{ path: 'src/index.ts', sha256: 'd'.repeat(64), size: 92 }], next_offset: 1, has_more: false,
      }, origin);
    }
    const fileMatch = pathname.match(new RegExp(`^/v1/engineering-runs/${RUN_ID}/source/(.+)/file$`));
    if (fileMatch && request.method === 'GET') {
      const lineage = decodeURIComponent(fileMatch[1]);
      return json(response, 200, {
        project_id: PROJECT_ID, run_id: RUN_ID, lineage_id: lineage, path: 'src/index.ts', sha256: 'd'.repeat(64), size: 92,
        availability: 'TEXT', text: "export const correlationStatus = 'verified';\nexport const operatorReview = true;\n",
      }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/source-diff` && request.method === 'GET') {
      return json(response, 200, {
        project_id: PROJECT_ID, run_id: RUN_ID, from_lineage: PARENT, to_lineage: CANDIDATE, unchanged_count: 0, changed_count: 1,
        files: [{ path: 'src/index.ts', change_type: 'MODIFIED', from_sha256: 'e'.repeat(64), from_size: 62, to_sha256: 'd'.repeat(64), to_size: 92, availability: 'TEXT', diff_text: "--- a/src/index.ts\n+++ b/src/index.ts\n+export const operatorReview = true;\n", truncated: false }], truncated: false,
      }, origin);
    }
    const evidenceMatch = pathname.match(new RegExp(`^/v1/engineering-runs/${RUN_ID}/attempts/([^/]+)/evidence$`));
    if (evidenceMatch && request.method === 'GET') {
      const attempt = evidenceMatch[1];
      const failed = attempt === TEST_FAILED_ATTEMPT;
      const stage = attempt === BUILD_ATTEMPT ? 'BUILD' : 'TEST';
      return json(response, 200, {
        project_id: PROJECT_ID, run_id: RUN_ID, attempt_id: attempt, stage, attempt_number: failed ? 1 : stage === 'TEST' ? 2 : 1,
        status: failed ? 'FAILED' : 'PASSED', program_id: 'protected-executor', model_id: null, tool_id: stage === 'BUILD' ? 'python-compile' : 'pytest',
        failure_code: failed ? 'TEST_FAILURE' : null, started_at: now, completed_at: now, availability: 'AVAILABLE',
        evidence: { tool_id: stage === 'BUILD' ? 'python-compile' : 'pytest', exit_code: failed ? 1 : 0, protected_success: !failed, redacted: false },
      }, origin);
    }
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

const web = staticServer();
const api = apiServer();
let browser;
try {
  await Promise.all([listen(web, 8770), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });

  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await desktop.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await desktop.getByRole('button', { name: 'Activity', exact: true }).click();
  await desktop.getByText('Run observability', { exact: true }).waitFor({ timeout: 8000 });
  await desktop.getByTestId('run-event-11').getByText('Operator review required before completion.').waitFor({ timeout: 8000 });
  await desktop.getByText('System Health', { exact: true }).waitFor();
  await desktop.getByText('REVIEW', { exact: true }).first().waitFor();

  await desktop.getByRole('button', { name: 'Pause View' }).click();
  await desktop.getByRole('button', { name: 'Jump to Latest' }).waitFor();
  await desktop.getByRole('button', { name: 'Jump to Latest' }).click();

  await desktop.getByRole('tab', { name: 'Code' }).click();
  await desktop.getByText(CANDIDATE, { exact: true }).click();
  await desktop.getByText('src/index.ts', { exact: true }).click();
  await desktop.getByText("export const correlationStatus = 'verified';", { exact: false }).waitFor();

  await desktop.getByRole('tab', { name: 'Diff' }).click();
  await desktop.getByText('MODIFIED · src/index.ts', { exact: true }).waitFor();
  await desktop.getByText('+export const operatorReview = true;', { exact: false }).waitFor();

  await desktop.getByRole('tab', { name: 'Terminal' }).click();
  await desktop.getByText('BUILD · #5', { exact: true }).click();
  await desktop.getByText('python-compile', { exact: true }).waitFor();

  await desktop.getByRole('tab', { name: 'Tests' }).click();
  await desktop.getByText('TEST · #6', { exact: true }).click();
  await desktop.getByText('TEST_FAILURE', { exact: true }).waitFor();

  await desktop.getByRole('tab', { name: 'Evidence' }).click();
  await desktop.getByText('GitHub', { exact: true }).waitFor();
  await desktop.getByText('Vercel', { exact: true }).waitFor();
  await desktop.getByText(/PR #165/).waitFor();
  await desktop.getByText(/preview-wave4-165/).waitFor();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await mobile.getByRole('tab', { name: 'Progress', exact: true }).click();
  await mobile.getByTestId('mobile-build-workspace').waitFor({ timeout: 8000 });
  await mobile.getByRole('button', { name: 'Open technical build details', exact: true }).click();
  await mobile.getByText('Run observability', { exact: true }).waitFor({ timeout: 8000 });
  await mobile.getByTestId('live-build-focused-navigation').waitFor();

  for (const section of ['Run', 'Activity', 'Code', 'Tests', 'Evidence', 'Health']) {
    assert(await mobile.getByRole('tab', { name: section, exact: true }).count() === 1, `Focused Live Build section ${section} is missing`);
  }
  const sectionTargets = await mobile.getByTestId('live-build-focused-navigation').getByRole('tab').evaluateAll((nodes) => nodes.map((node) => ({ width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height })));
  assert(sectionTargets.every((target) => target.height >= 43.5 && target.width >= 44), 'Focused Live Build section targets must remain at least 44pt');

  await mobile.getByRole('tab', { name: 'Run', exact: true }).click();
  await mobile.getByText('CURRENT AUTHORITATIVE STAGE', { exact: true }).waitFor();
  await mobile.getByText('RECOVERY / RETRY', { exact: true }).waitFor();

  await mobile.getByRole('tab', { name: 'Activity', exact: true }).click();
  await mobile.getByTestId('run-event-11').getByText('Operator review required before completion.').waitFor();
  const activityControls = [
    mobile.getByRole('button', { name: 'Follow Live' }),
    mobile.getByRole('button', { name: 'Pause View' }),
    mobile.getByRole('button', { name: 'Jump to Latest' }),
  ];
  for (const control of activityControls) {
    const box = await control.boundingBox();
    assert(box && box.height >= 43.5 && box.width >= 44, 'Observer controls must remain at least 44pt on phone');
  }
  await mobile.getByRole('button', { name: 'Pause View' }).click();
  await mobile.getByRole('button', { name: 'Jump to Latest' }).click();

  await mobile.getByRole('tab', { name: 'Code', exact: true }).click();
  await mobile.getByRole('button', { name: 'Inspect file src/index.ts' }).waitFor({ timeout: 8000 });
  await mobile.getByRole('button', { name: 'Inspect file src/index.ts' }).click();
  await mobile.getByText("export const correlationStatus = 'verified';", { exact: false }).waitFor();
  const fileTarget = await mobile.getByRole('button', { name: 'Inspect file src/index.ts' }).boundingBox();
  assert(fileTarget && fileTarget.height >= 43.5, 'Mobile file selector target must remain at least 44pt');
  await mobile.getByRole('tab', { name: 'Show source diff' }).click();
  await mobile.getByText('MODIFIED · src/index.ts', { exact: true }).waitFor();
  await mobile.getByText('+export const operatorReview = true;', { exact: false }).waitFor();

  await mobile.getByRole('tab', { name: 'Tests', exact: true }).click();
  await mobile.getByRole('button', { name: 'Inspect TEST attempt sequence 6' }).click();
  await mobile.getByText('TEST_FAILURE', { exact: true }).waitFor();
  await mobile.getByRole('tab', { name: 'Show bounded command output' }).click();
  await mobile.getByRole('button', { name: 'Inspect BUILD attempt sequence 5' }).click();
  await mobile.getByText('python-compile', { exact: true }).waitFor();

  await mobile.getByRole('tab', { name: 'Evidence', exact: true }).click();
  await mobile.getByText('GitHub', { exact: true }).waitFor();
  await mobile.getByText('Vercel', { exact: true }).waitFor();

  await mobile.getByRole('tab', { name: 'Health', exact: true }).click();
  await mobile.getByText('System Health', { exact: true }).waitFor();
  await mobile.getByText('Active Run', { exact: true }).waitFor();
  const mobileOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert(mobileOverflow <= 1, `Phone Live Build introduced page-level horizontal overflow: ${mobileOverflow}px`);

  const tablet = await browser.newPage({ viewport: { width: 834, height: 1112 } });
  await tablet.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await tablet.getByRole('button', { name: 'Activity', exact: true }).click();
  await tablet.getByTestId('live-build-focused-navigation').waitFor({ timeout: 8000 });
  await tablet.getByRole('tab', { name: 'Code', exact: true }).click();
  const tabletFileSelector = tablet.getByRole('button', { name: 'Inspect file src/index.ts' });
  await tabletFileSelector.waitFor({ timeout: 8000 });
  await tabletFileSelector.click();
  await tablet.getByText("export const correlationStatus = 'verified';", { exact: false }).waitFor();
  const tabletSelector = await tabletFileSelector.boundingBox();
  const tabletWorkspace = await tablet.getByTestId('live-build-workspace').boundingBox();
  assert(tabletSelector && tabletWorkspace && tabletSelector.width >= tabletWorkspace.width * 0.9 && tabletSelector.height >= 43.5, 'Tablet source selector should fill the focused Live Build workspace and remain at least 44pt');
  await tablet.getByRole('tab', { name: 'Tests', exact: true }).click();
  await tablet.getByRole('button', { name: 'Inspect TEST attempt sequence 6' }).click();
  await tablet.getByText('TEST_FAILURE', { exact: true }).waitFor();
  const tabletOverflow = await tablet.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert(tabletOverflow <= 1, `Tablet Live Build introduced page-level horizontal overflow: ${tabletOverflow}px`);

  await mobile.getByLabel('Back to conversation').click();
  await mobile.getByLabel('Message Parallax').waitFor();

  engineeringRun.state = 'FAILED';
  engineeringRun.resume_stage = 'IMPLEMENT';
  engineeringRun.last_failure_code = 'AUTONOMOUS_IMPLEMENT_FAILED';
  engineeringRun.revision = 3;
  engineeringRun.attempts = [{ id: '77777777-7777-4777-8777-777777777778', stage: 'IMPLEMENT', attempt_number: 1, status: 'FAILED', failure_code: 'AUTONOMOUS_IMPLEMENT_FAILED', evidence: { error_class: 'ImplementationContractError', mutation_applied: false }, started_at: now, completed_at: now }];
  events.splice(3);

  const failedMobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await failedMobile.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await failedMobile.getByRole('tab', { name: 'Progress', exact: true }).click();
  await failedMobile.getByTestId('mobile-build-workspace').waitFor({ timeout: 8000 });
  await failedMobile.getByRole('button', { name: 'Open technical build details', exact: true }).click();
  await failedMobile.getByRole('tab', { name: 'Run', exact: true }).click();
  await failedMobile.getByTestId('live-build-durable-failure').waitFor({ timeout: 8000 });
  await failedMobile.getByText('IMPLEMENT failed', { exact: true }).waitFor();
  await failedMobile.getByText('AUTONOMOUS_IMPLEMENT_FAILED', { exact: true }).waitFor();
  await failedMobile.getByRole('tab', { name: 'Activity', exact: true }).click();
  await failedMobile.getByText('Engineering Run', { exact: true }).waitFor();
  await failedMobile.getByText('Failed', { exact: true }).first().waitFor();
  await failedMobile.getByText(/AUTONOMOUS_IMPLEMENT_FAILED/).first().waitFor();

  assert(await desktop.locator('[data-testid="live-build-workspace"]').count() === 1, 'Desktop Live Build workspace did not mount exactly once');
  console.log(JSON.stringify({
    desktopLiveBuild: true,
    persistedReviewBoundary: true,
    pauseViewObservationOnly: true,
    protectedCodeDiffEvidence: true,
    providerEvidenceBacked: true,
    focusedPhoneComposition: true,
    focusedTabletComposition: true,
    minimumObserverTargets: true,
    mobileCodeDiffTestsEvidenceHealth: true,
    mobileLiveBuildEntryAndReturn: true,
    durableFailedRunFallback: true,
  }, null, 2));
} finally {
  await browser?.close();
  await new Promise((resolve) => web.close(resolve));
  await new Promise((resolve) => api.close(resolve));
}
