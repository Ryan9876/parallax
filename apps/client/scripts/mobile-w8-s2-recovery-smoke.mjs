import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const evidenceDir = new URL('../visual-evidence/', import.meta.url).pathname;
mkdirSync(evidenceDir, { recursive: true });

const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

const PROJECT_ID = '12121212-1212-4212-8212-121212121212';
const CONVERSATION_ID = '33333333-3333-4333-8333-333333333333';
const SPEC_ID = '44444444-4444-4444-8444-444444444444';
const RUN_ID = '55555555-5555-4555-8555-555555555555';
const FAILURE_DETAIL = "Parallax couldn't prepare this project for building yet. Your plan and work are still saved. Try again.";

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

const project = {
  id: PROJECT_ID,
  slug: 'w8-s2-recovery',
  name: 'W8 S2 Recovery Project',
  description: null,
  repository_ref: 'github:owner/w8-s2-recovery',
  workspace_ref: `project:${PROJECT_ID}`,
  status: 'active',
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
};

const conversation = {
  id: CONVERSATION_ID,
  title: 'Recover a protected build safely',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.21.1',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
  messages: [{
    id: 'w8-s2-user-1',
    role: 'user',
    content: 'Continue the approved build.',
    status: 'complete',
    created_at: '2026-08-28T12:00:00Z',
  }],
};

const workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Recovery behavior',
  objective: 'Keep saved work intact and provide a safe retry when continuation cannot proceed.',
  constraints: ['Do not fabricate run progress.'],
  acceptance_criteria: ['Show plain recovery guidance.', 'Retry from the same durable run revision.'],
  risks: ['A provider failure could otherwise look like a frozen build.'],
  open_questions: [],
  confidence: 0.99,
  program_version: 'w8-s2-recovery-smoke',
  model_id: 'test-model',
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
  approved_at: '2026-08-28T12:01:00Z',
};

const now = '2026-08-28T12:02:00Z';
let engineeringRun = {
  id: RUN_ID,
  conversation_id: CONVERSATION_ID,
  spec_id: conversation.spec_id,
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  work_specification_id: SPEC_ID,
  work_specification_revision: workSpecification.revision,
  work_specification_digest: 'w8-s2-recovery-digest',
  binding_status: 'APPROVED_SPEC_BOUND',
  acceptance_criteria: workSpecification.acceptance_criteria.map((text, index) => ({ id: `AC-${String(index + 1).padStart(2, '0')}`, text })),
  state: 'PLAN',
  resume_stage: null,
  revision: 1,
  workspace_ref: 'test://w8-s2-recovery',
  last_failure_code: null,
  completed_at: null,
  created_at: now,
  updated_at: now,
  attempts: [],
};
let autonomyCalls = 0;

function apiServer() {
  function cors(response, origin) {
    response.setHeader('access-control-allow-origin', origin ?? '*');
    response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization');
    response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
  }

  function json(response, status, value, origin) {
    cors(response, origin);
    const encoded = Buffer.from(JSON.stringify(value));
    response.writeHead(status, { 'content-type': 'application/json', 'content-length': encoded.length });
    response.end(encoded);
  }

  async function body(request) {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
  }

  return createServer(async (request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') {
      cors(response, origin);
      response.writeHead(204);
      response.end();
      return;
    }

    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/projects' && request.method === 'GET') return json(response, 200, [project], origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, engineeringRun, origin);
    if (pathname === `/v1/engineering-runs/${RUN_ID}/autonomous` && request.method === 'POST') {
      const payload = await body(request);
      autonomyCalls += 1;
      assert(payload.expected_revision === 1, 'w8-s2 recovery: retry must use the same durable PLAN revision after a request-level failure');
      if (autonomyCalls === 1) return json(response, 503, { detail: FAILURE_DETAIL }, origin);

      const completedAt = new Date().toISOString();
      engineeringRun = {
        ...engineeringRun,
        state: 'REVIEW',
        revision: 2,
        updated_at: completedAt,
        attempts: [{
          id: '66666666-6666-4666-8666-666666666666',
          stage: 'PLAN',
          attempt_number: 1,
          status: 'PASSED',
          failure_code: null,
          evidence: { protected_success: true },
          started_at: completedAt,
          completed_at: completedAt,
        }],
      };
      return json(response, 200, {
        run: engineeringRun,
        stop_reason: 'REVIEW_REQUIRED',
        steps: [{ stage: 'PLAN', outcome: 'PASSED', attempt_id: '66666666-6666-4666-8666-666666666666', replayed: false, tool_id: 'protected-plan' }],
      }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events` && request.method === 'GET') return json(response, 200, { events: [], next_after_sequence: 0, has_more: false }, origin);
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events/stream` && request.method === 'GET') {
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      response.end(': ready\n\n');
      return;
    }
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

const staticSite = staticServer();
const api = apiServer();
let browser;

try {
  await Promise.all([listen(staticSite, 8767), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });

  await page.goto('http://127.0.0.1:8767', { waitUntil: 'networkidle' });
  await page.getByTestId('mobile-guided-shell').waitFor({ timeout: 10000 });
  await page.getByText('Parallax couldn’t continue this step', { exact: true }).waitFor({ timeout: 10000 });

  await page.getByRole('tab', { name: 'Progress' }).click();
  await page.getByTestId('mobile-build-workspace').waitFor({ timeout: 5000 });
  await page.getByText('Something needs attention', { exact: true }).waitFor();
  await page.getByText(/Your saved work is still here\. Try again\./).waitFor();

  const retry = page.getByRole('button', { name: 'Try again' });
  const retryBox = await retry.boundingBox();
  assert(retryBox && retryBox.height >= 44, 'w8-s2 recovery: Try again touch target is smaller than 44px');
  assert(await page.getByText(`System message: ${FAILURE_DETAIL}`, { exact: true }).count() === 0, 'w8-s2 recovery: raw request evidence leaked before Technical details was opened');

  await page.getByRole('button', { name: 'Show technical details and evidence' }).click();
  await page.getByText(`System message: ${FAILURE_DETAIL}`, { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Hide technical details and evidence' }).click();

  await retry.click();
  await page.getByText('Ready for your review', { exact: true }).waitFor({ timeout: 10000 });
  assert(autonomyCalls === 2, `w8-s2 recovery: expected one failed continuation plus one retry, got ${autonomyCalls}`);

  await page.screenshot({ path: join(evidenceDir, 'w8-s2-mobile-recovery.png'), fullPage: true });
  assert(errors.length === 0, `w8-s2 recovery: browser errors detected: ${errors.join(' | ')}`);
  console.log('PASS: W8-S2 mobile recovery keeps durable progress visible, hides technical evidence by default, and exposes a 44px retry action.');
} finally {
  if (browser) await browser.close();
  await Promise.all([
    new Promise((resolve) => staticSite.close(resolve)),
    new Promise((resolve) => api.close(resolve)),
  ]);
}
