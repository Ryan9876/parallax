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
  slug: 'wave8-mobile-project',
  name: 'Wave 8 Mobile Project',
  description: null,
  repository_ref: 'github:owner/wave8-mobile-project',
  workspace_ref: `project:${PROJECT_ID}`,
  status: 'active',
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
};

const conversation = {
  id: CONVERSATION_ID,
  title: 'Make the mobile experience easier to follow',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.20.3',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
  messages: [{
    id: 'wave8-user-1',
    role: 'user',
    content: 'Make the mobile experience easier to follow and use plain language.',
    status: 'complete',
    created_at: '2026-08-28T12:00:00Z',
  }],
};

let workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 4,
  status: 'DRAFT',
  title: 'Mobile experience clarity',
  objective: 'Make the mobile experience easy to understand while preserving the existing governed build flow.',
  constraints: ['Keep server-owned build state authoritative.', 'Keep technical evidence available on demand.'],
  acceptance_criteria: [
    'Users can see where they are in the process.',
    'Primary mobile text is comfortably readable without zooming.',
    'Primary product language is understandable without software-engineering knowledge.',
    'Technical details remain available without dominating the default view.',
  ],
  risks: ['Simplifying labels must not imply progress the server has not recorded.'],
  open_questions: [],
  confidence: 0.94,
  program_version: 'wave8-mobile-smoke',
  model_id: 'test-model',
  created_at: '2026-08-28T12:00:00Z',
  updated_at: '2026-08-28T12:00:00Z',
  approved_at: null,
};

let engineeringRun = null;

function activatedRun() {
  const now = new Date().toISOString();
  return {
    id: RUN_ID,
    conversation_id: CONVERSATION_ID,
    spec_id: conversation.spec_id,
    project_id: PROJECT_ID,
    project_binding_status: 'PROJECT_BOUND',
    work_specification_id: SPEC_ID,
    work_specification_revision: workSpecification.revision,
    work_specification_digest: 'wave8-mobile-digest',
    binding_status: 'APPROVED_SPEC_BOUND',
    acceptance_criteria: workSpecification.acceptance_criteria.map((text, index) => ({ id: `AC-${String(index + 1).padStart(2, '0')}`, text })),
    state: 'PLAN',
    resume_stage: null,
    revision: 1,
    workspace_ref: 'test://wave8-mobile',
    last_failure_code: null,
    completed_at: null,
    created_at: now,
    updated_at: now,
    attempts: [],
  };
}

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
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification.status === 'APPROVED' ? workSpecification : null, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, engineeringRun, origin);
    if (pathname === '/v1/engineering-runs/activate' && request.method === 'POST') {
      engineeringRun = engineeringRun ?? activatedRun();
      return json(response, 200, engineeringRun, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/autonomous` && request.method === 'POST') {
      const payload = await body(request);
      assert(engineeringRun?.state === 'PLAN', 'wave8 mobile: autonomy must begin from the activated PLAN state');
      assert(payload.expected_revision === engineeringRun.revision, 'wave8 mobile: autonomous continuation used a stale run revision');
      const now = new Date().toISOString();
      engineeringRun = {
        ...engineeringRun,
        state: 'REVIEW',
        revision: engineeringRun.revision + 1,
        updated_at: now,
        attempts: [{
          id: '66666666-6666-4666-8666-666666666666',
          stage: 'PLAN',
          attempt_number: 1,
          status: 'PASSED',
          failure_code: null,
          evidence: { protected_success: true },
          started_at: now,
          completed_at: now,
        }],
      };
      return json(response, 200, {
        run: engineeringRun,
        stop_reason: 'REVIEW_REQUIRED',
        steps: [{ stage: 'PLAN', outcome: 'SUCCEEDED', attempt_id: '66666666-6666-4666-8666-666666666666', replayed: false, tool_id: 'protected-plan' }],
      }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events` && request.method === 'GET') return json(response, 200, { events: [], next_after_sequence: 0, has_more: false }, origin);
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events/stream` && request.method === 'GET') {
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      response.end(': ready\n\n');
      return;
    }
    if (pathname === `/v1/work-specifications/${SPEC_ID}/approve` && request.method === 'POST') {
      const now = new Date().toISOString();
      workSpecification = { ...workSpecification, status: 'APPROVED', approved_at: now, updated_at: now };
      return json(response, 200, workSpecification, origin);
    }
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

async function fontSize(locator) {
  return locator.evaluate((element) => Number.parseFloat(getComputedStyle(element).fontSize));
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
  await page.getByLabel('Review build plan').waitFor({ timeout: 10000 });

  assert(await page.getByRole('tab').count() === 3, 'wave8 mobile: main navigation must expose exactly three destinations');
  for (const label of ['Chat', 'Progress', 'Project']) {
    const tab = page.getByRole('tab', { name: label });
    const box = await tab.boundingBox();
    assert(box && box.height >= 44, `wave8 mobile: ${label} navigation target is smaller than 44px`);
    assert(await fontSize(tab.getByText(label, { exact: true })) >= 14, `wave8 mobile: ${label} navigation text is smaller than 14px`);
  }

  const contextTitle = page.getByText('Review your build plan', { exact: true });
  assert(await fontSize(contextTitle) >= 20, 'wave8 mobile: primary context title is too small');
  assert(await fontSize(page.getByText('Check the plan below, then approve it only when it matches what you want Parallax to build.', { exact: true })) >= 15, 'wave8 mobile: primary context copy is too small');

  const navBox = await page.getByTestId('mobile-bottom-navigation').boundingBox();
  const inputBox = await page.getByLabel('Message Parallax').boundingBox();
  assert(navBox && inputBox, 'wave8 mobile: navigation or composer geometry was not measurable');
  assert(inputBox.y + inputBox.height <= navBox.y + 1, 'wave8 mobile: composer overlaps bottom navigation');

  await page.getByLabel('Review build plan').click();
  await page.getByTestId('mobile-specification-detail').waitFor({ timeout: 5000 });
  await page.getByText('Review your build plan', { exact: true }).waitFor();
  for (const heading of ['WHAT YOU WANT', 'WHAT SUCCESS LOOKS LIKE', 'IMPORTANT LIMITS', 'THINGS TO WATCH']) {
    await page.getByText(heading, { exact: true }).waitFor();
  }
  assert(await page.getByText('System object: Work Specification', { exact: true }).count() === 0, 'wave8 mobile: technical terminology should be hidden by default');

  const approve = page.getByLabel('Approve plan and continue');
  const update = page.getByLabel('Update build plan');
  for (const [name, locator] of [['approve', approve], ['update', update], ['back', page.getByLabel('Back to Chat')]]) {
    const box = await locator.boundingBox();
    assert(box && box.height >= 44, `wave8 mobile: ${name} target is smaller than 44px`);
  }
  assert(await page.getByLabel('Message Parallax').count() === 0, 'wave8 mobile: composer should not compete with full-screen plan review');

  await page.getByLabel('Show technical details').click();
  await page.getByText('System object: Work Specification', { exact: true }).waitFor();
  await page.getByLabel('Hide technical details').click();
  await page.screenshot({ path: `${evidenceDir}/wave8-mobile-plan-review.png`, fullPage: true });

  await approve.click();
  await page.getByText('Approved plan', { exact: true }).waitFor({ timeout: 5000 });
  await page.getByLabel('Back to Chat').click();
  await page.getByRole('tab', { name: 'Progress' }).click();
  await page.getByTestId('mobile-build-workspace').waitFor({ timeout: 5000 });
  await page.getByText('Where things stand', { exact: true }).waitFor();
  for (const step of ['Define', 'Plan', 'Create', 'Check', 'Review']) {
    await page.getByText(step, { exact: true }).first().waitFor();
  }
  await page.getByText('Ready for your review', { exact: true }).waitFor();
  assert(await page.getByText('System stage: REVIEW', { exact: true }).count() === 0, 'wave8 mobile: raw server stage leaked into default progress view');
  await page.getByLabel('Show technical details and evidence').click();
  await page.getByText('System stage: REVIEW', { exact: true }).waitFor();
  await page.screenshot({ path: `${evidenceDir}/wave8-mobile-progress.png`, fullPage: true });

  conversation.status = 'SPEC_AMENDMENT';
  conversation.updated_at = new Date().toISOString();
  await page.reload({ waitUntil: 'networkidle' });
  await page.getByTestId('mobile-spec-amendment').waitFor({ timeout: 5000 });
  await page.getByText('This is different from the plan you approved', { exact: true }).waitFor();
  for (const label of ['Start as a new goal', 'Continue approved work']) {
    const box = await page.getByLabel(label).boundingBox();
    assert(box && box.height >= 44, `wave8 mobile: ${label} is not a practical touch target`);
  }
  await page.screenshot({ path: `${evidenceDir}/wave8-mobile-scope-change.png`, fullPage: true });

  assert(errors.length === 0, `wave8 mobile: browser errors: ${errors.join(' | ')}`);
  console.log(JSON.stringify({
    viewport: { width: 390, height: 844 },
    navigation: ['Chat', 'Progress', 'Project'],
    journey: ['Define', 'Plan', 'Create', 'Check', 'Review'],
    plainLanguageDefault: true,
    technicalDetailDisclosure: true,
    primaryTextMinimums: { navigation: 14, body: 15, contextTitle: 20 },
    touchTargets: '>=44px',
    approvalAndReviewHandoff: true,
    scopeChangeLanguage: 'plain',
  }, null, 2));
} finally {
  if (browser) await browser.close();
  await Promise.all([
    new Promise((resolve) => staticSite.close(resolve)),
    new Promise((resolve) => api.close(resolve)),
  ]);
}