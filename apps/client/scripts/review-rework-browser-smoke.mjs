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
const now = '2026-09-02T21:30:00Z';

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

const project = {
  id: PROJECT_ID,
  slug: 'review-rework-smoke',
  name: 'Review Rework Smoke',
  description: null,
  repository_ref: null,
  workspace_ref: `project:${PROJECT_ID}`,
  delivery_mode: 'source-only',
  status: 'ACTIVE',
  created_at: now,
  updated_at: now,
};

const conversation = {
  id: CONVERSATION_ID,
  title: 'Review correction workflow',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.23.41',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: now,
  updated_at: now,
  messages: [{ id: 'm1', role: 'assistant', content: 'The result is ready for review.', status: 'complete', created_at: now }],
};

const specification = {
  id: SPECIFICATION_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Review correction workflow',
  objective: 'Correct the reviewed result without changing approved scope.',
  constraints: ['Keep the approved Work Specification unchanged.'],
  acceptance_criteria: [
    'Imported records remain renderable after malformed input.',
    'The delivered repository contains automated regression tests.',
  ],
  risks: [],
  open_questions: [],
  confidence: 0.99,
  program_version: 'work-spec-v0.23.41',
  model_id: 'review-rework-smoke',
  created_at: now,
  updated_at: now,
  approved_at: now,
};

function run(state, revision) {
  return {
    id: RUN_ID,
    conversation_id: CONVERSATION_ID,
    spec_id: 'P2-V0.23.41',
    project_id: PROJECT_ID,
    project_binding_status: 'PROJECT_BOUND',
    work_specification_id: SPECIFICATION_ID,
    work_specification_revision: 1,
    work_specification_digest: 'c'.repeat(64),
    binding_status: 'APPROVED_SPEC_BOUND',
    acceptance_criteria: [
      { id: 'AC-01', text: specification.acceptance_criteria[0] },
      { id: 'AC-02', text: specification.acceptance_criteria[1] },
    ],
    state,
    resume_stage: null,
    revision,
    workspace_ref: null,
    last_failure_code: null,
    completed_at: null,
    created_at: now,
    updated_at: now,
    attempts: [],
  };
}

const reviewRun = run('REVIEW', 2);
const planRun = run('PLAN', 3);
const correctedReviewRun = run('REVIEW', 4);
let currentRun = reviewRun;
let reviewRequests = [];
let autonomyRequests = [];

function cors(response, origin) {
  response.setHeader('access-control-allow-origin', origin ?? '*');
  response.setHeader('access-control-allow-credentials', 'true');
  response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization,X-Parallax-Session');
  response.setHeader('access-control-allow-methods', 'GET,POST,PATCH,OPTIONS');
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
    if (pathname === '/v1/projects' && request.method === 'GET') return json(response, 200, [project], origin);
    if (pathname === `/v1/projects/${PROJECT_ID}` && request.method === 'GET') return json(response, 200, project, origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, specification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, specification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, currentRun, origin);

    if (pathname === `/v1/engineering-runs/${RUN_ID}/review-rework` && request.method === 'POST') {
      reviewRequests.push(await body(request));
      currentRun = planRun;
      return json(response, 200, { run: planRun }, origin);
    }

    if (pathname === `/v1/engineering-runs/${RUN_ID}/autonomous` && request.method === 'POST') {
      autonomyRequests.push(await body(request));
      currentRun = correctedReviewRun;
      return json(response, 200, {
        run: correctedReviewRun,
        stop_reason: 'REVIEW_REQUIRED',
        steps: [{ stage: 'PLAN', outcome: 'SUCCEEDED', attempt_id: null, replayed: false, tool_id: 'protected-plan' }],
      }, origin);
    }

    return json(response, 404, { detail: 'not found' }, origin);
  });
}

async function exercise(page, { mobile }) {
  currentRun = reviewRun;
  reviewRequests = [];
  autonomyRequests = [];

  await page.goto('http://127.0.0.1:8772', { waitUntil: 'networkidle' });
  if (mobile) {
    await page.getByRole('tab', { name: 'Progress' }).click();
  }

  const panel = page.getByTestId('review-rework-panel');
  await panel.waitFor({ state: 'visible' });
  await page.getByRole('checkbox', { name: /AC-01:/ }).click();
  await page.getByLabel('What should Parallax change').fill('Reject malformed imported records before they can corrupt persisted browser state.');
  await page.getByRole('button', { name: 'Request changes' }).click();

  await page.waitForFunction(() => document.body.innerText.includes('Ready for your review'));
  assert(reviewRequests.length === 1, `${mobile ? 'mobile' : 'desktop'} submitted ${reviewRequests.length} REVIEW rework requests`);
  const request = reviewRequests[0];
  assert(request.expected_revision === 2, `${mobile ? 'mobile' : 'desktop'} rework was not bound to exact REVIEW revision`);
  assert(Array.isArray(request.acceptance_ids) && request.acceptance_ids.length === 1 && request.acceptance_ids[0] === 'AC-01', `${mobile ? 'mobile' : 'desktop'} rework lost selected acceptance identity`);
  assert(request.finding === 'Reject malformed imported records before they can corrupt persisted browser state.', `${mobile ? 'mobile' : 'desktop'} rework finding drifted`);
  assert(typeof request.operation_key === 'string' && request.operation_key.startsWith(`review-rework-${RUN_ID}-2-`), `${mobile ? 'mobile' : 'desktop'} rework operation identity is not revision-bound`);
  assert(autonomyRequests.length === 1, `${mobile ? 'mobile' : 'desktop'} did not hand the returned PLAN revision into bounded autonomy`);
  assert(autonomyRequests[0].expected_revision === 3, `${mobile ? 'mobile' : 'desktop'} autonomy did not bind the rework PLAN revision`);
  assert(autonomyRequests[0].operation_key === `autonomous-auto-${RUN_ID}-3`, `${mobile ? 'mobile' : 'desktop'} rework autonomy identity drifted`);
}

const web = staticServer();
const api = apiServer();
let browser;
try {
  await Promise.all([listen(web, 8772), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });

  const desktop = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await exercise(desktop, { mobile: false });
  await desktop.close();

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await exercise(mobile, { mobile: true });
  await mobile.close();

  console.log('PASS REVIEW rework desktop/mobile interaction and bounded autonomy handoff');
} finally {
  if (browser) await browser.close();
  await Promise.all([close(web), close(api)]);
}
