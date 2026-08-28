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
const SPECIFICATION_ID = '22222222-2222-4222-8222-222222222222';
const RUN_ID = '44444444-4444-4444-8444-444444444444';
const now = '2026-08-28T03:50:00Z';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

function close(server) {
  return new Promise((resolve) => server.close(() => resolve()));
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

const conversation = {
  id: CONVERSATION_ID,
  title: 'Mobile autonomous handoff',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.20.3',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: now,
  updated_at: now,
  messages: [{ id: 'm1', role: 'assistant', content: 'Approved build ready.', status: 'complete', created_at: now }],
};

const specification = {
  id: SPECIFICATION_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Mobile autonomous handoff',
  objective: 'Continue the protected build after approval.',
  constraints: ['Preserve server-owned execution authority.'],
  acceptance_criteria: ['Approved PLAN run continues without a mobile dead end.'],
  risks: [],
  open_questions: [],
  confidence: 0.98,
  program_version: 'work-spec-v0.20.3',
  model_id: 'handoff-smoke',
  created_at: now,
  updated_at: now,
  approved_at: now,
};

function run(state, revision, overrides = {}) {
  return {
    id: RUN_ID,
    conversation_id: CONVERSATION_ID,
    spec_id: 'P2-V0.20.3',
    project_id: PROJECT_ID,
    project_binding_status: 'PROJECT_BOUND',
    work_specification_id: SPECIFICATION_ID,
    work_specification_revision: 1,
    work_specification_digest: 'c'.repeat(64),
    binding_status: 'APPROVED_SPEC_BOUND',
    acceptance_criteria: [{ id: 'AC-01', text: specification.acceptance_criteria[0] }],
    state,
    resume_stage: null,
    revision,
    workspace_ref: null,
    last_failure_code: null,
    completed_at: null,
    created_at: now,
    updated_at: now,
    attempts: [],
    ...overrides,
  };
}

const planRun = run('PLAN', 1);
const reviewRun = run('REVIEW', 2);
let currentRun = null;
let activateRequests = [];
let autonomyRequests = [];

function cors(response, origin) {
  response.setHeader('access-control-allow-origin', origin ?? '*');
  response.setHeader('access-control-allow-credentials', 'true');
  response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization');
  response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
}

function json(response, status, payload, origin) {
  cors(response, origin);
  response.writeHead(status, { 'content-type': 'application/json' });
  response.end(JSON.stringify(payload));
}

async function body(request) {
  let raw = '';
  for await (const chunk of request) raw += chunk;
  return raw ? JSON.parse(raw) : {};
}

function apiServer() {
  return createServer(async (request, response) => {
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
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, specification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, specification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, currentRun, origin);

    if (pathname === '/v1/engineering-runs/activate' && request.method === 'POST') {
      activateRequests.push(await body(request));
      currentRun = planRun;
      return json(response, 200, planRun, origin);
    }

    if (pathname === `/v1/engineering-runs/${RUN_ID}/autonomous` && request.method === 'POST') {
      autonomyRequests.push(await body(request));
      currentRun = reviewRun;
      return json(response, 200, {
        run: reviewRun,
        stop_reason: 'REVIEW_REQUIRED',
        steps: [{ stage: 'PLAN', outcome: 'SUCCEEDED', attempt_id: null, replayed: false, tool_id: 'protected-plan' }],
      }, origin);
    }

    return json(response, 404, { detail: 'not found' }, origin);
  });
}

async function waitFor(predicate, message, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(message);
}

const web = staticServer();
const api = apiServer();
let browser;
try {
  await Promise.all([listen(web, 8770), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

  // First load: approved Work Specification exists but no run yet. The client
  // activates it, receives PLAN, and must immediately enter bounded autonomy.
  await page.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await waitFor(() => autonomyRequests.length >= 1, 'approved PLAN run never entered bounded autonomy');
  assert(activateRequests.length === 1, `expected one activation request, received ${activateRequests.length}`);
  assert(activateRequests[0].conversation_id === CONVERSATION_ID, 'activation lost canonical conversation identity');
  assert(activateRequests[0].work_specification_id === SPECIFICATION_ID, 'activation lost approved Work Specification identity');
  assert(autonomyRequests.length === 1, `expected one autonomous handoff, received ${autonomyRequests.length}`);
  assert(autonomyRequests[0].expected_revision === 1, 'autonomous handoff did not bind the exact activated revision');
  assert(autonomyRequests[0].operation_key === `autonomous-auto-${RUN_ID}-1`, 'automatic autonomy identity is not deterministic/replay-safe');

  // Reconnect: an already-existing PLAN run must continue without creating a
  // second run. This reproduces the mobile screenshot state directly.
  currentRun = planRun;
  activateRequests = [];
  autonomyRequests = [];
  await page.reload({ waitUntil: 'networkidle' });
  await waitFor(() => autonomyRequests.length >= 1, 'reconnected PLAN run remained parked without bounded autonomy');
  assert(activateRequests.length === 0, 'reconnect must not create/activate a replacement run');
  assert(autonomyRequests.length === 1, `reconnect attempted autonomy ${autonomyRequests.length} times`);
  assert(autonomyRequests[0].operation_key === `autonomous-auto-${RUN_ID}-1`, 'reconnect must replay the same exact-revision automatic operation identity');

  // REVIEW is a protected handoff boundary and must never be auto-continued.
  currentRun = reviewRun;
  autonomyRequests = [];
  await page.reload({ waitUntil: 'networkidle' });
  await new Promise((resolve) => setTimeout(resolve, 400));
  assert(autonomyRequests.length === 0, 'REVIEW must not auto-continue');

  console.log('PASS mobile Engineering Run approved/reconnect autonomy handoff');
} finally {
  if (browser) await browser.close();
  await Promise.all([close(web), close(api)]);
}
