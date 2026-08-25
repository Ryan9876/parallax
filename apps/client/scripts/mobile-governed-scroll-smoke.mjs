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

const PROJECT_ID = '10101010-1010-4010-8010-101010101010';
const CONVERSATION_ID = '20202020-2020-4020-8020-202020202020';
const SPEC_ID = '30303030-3030-4030-8030-303030303030';
const RUN_ID = '40404040-4040-4040-8040-404040404040';
const now = '2026-08-25T21:40:00Z';

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

const conversation = {
  id: CONVERSATION_ID,
  title: 'Mobile governed scroll proof',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.13.0',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: now,
  updated_at: now,
  messages: [
    {
      id: 'mobile-scroll-user',
      role: 'user',
      content: 'Update the Parallax logo with a small governed visual change.',
      status: 'complete',
      created_at: now,
    },
    {
      id: 'mobile-scroll-assistant',
      role: 'assistant',
      content: 'The approved work specification is bound to an active implementation run. Review the persisted execution evidence and controls below.',
      status: 'complete',
      created_at: now,
    },
  ],
};

const workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Add slow continuous rotation to the Parallax logo',
  objective: 'Apply one bounded logo motion adjustment without changing protected execution authority.',
  constraints: [
    'Keep the existing application shell and responsive composition.',
    'Preserve protected execution and provider boundaries.',
  ],
  acceptance_criteria: [
    'The logo change remains bounded to the approved visual objective.',
    'Mobile remains usable with natural vertical scrolling.',
    'The composer remains reachable while governed execution evidence is visible.',
    'Protected execution authority remains server-owned.',
    'No unrelated application behavior changes.',
  ],
  risks: ['Tall governed execution context can exceed a phone viewport.'],
  open_questions: [],
  confidence: 0.99,
  program_version: 'mobile-governed-scroll-smoke',
  model_id: 'test-model',
  created_at: now,
  updated_at: now,
  approved_at: now,
};

const engineeringRun = {
  id: RUN_ID,
  conversation_id: CONVERSATION_ID,
  spec_id: 'P2-V0.13.0',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  work_specification_id: SPEC_ID,
  work_specification_revision: 1,
  work_specification_digest: 'a'.repeat(64),
  binding_status: 'APPROVED_SPEC_BOUND',
  acceptance_criteria: workSpecification.acceptance_criteria.map((text, index) => ({ id: `AC-0${index + 1}`, text })),
  state: 'IMPLEMENT',
  resume_stage: null,
  revision: 2,
  workspace_ref: null,
  last_failure_code: null,
  completed_at: null,
  created_at: now,
  updated_at: now,
  attempts: [
    { id: '50505050-5050-4050-8050-505050505050', stage: 'SPECIFY', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
    { id: '60606060-6060-4060-8060-606060606060', stage: 'PLAN', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
  ],
};

function cors(response, origin) {
  response.setHeader('access-control-allow-origin', origin ?? '*');
  response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization');
  response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
}

function json(response, status, body, origin) {
  cors(response, origin);
  const encoded = Buffer.from(JSON.stringify(body));
  response.writeHead(status, { 'content-type': 'application/json', 'content-length': encoded.length });
  response.end(encoded);
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
    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, engineeringRun, origin);
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

function scrollGeometry(node) {
  let current = node.parentElement;
  while (current) {
    const style = getComputedStyle(current);
    if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
      const rect = current.getBoundingClientRect();
      return {
        scrollTop: current.scrollTop,
        scrollHeight: current.scrollHeight,
        clientHeight: current.clientHeight,
        top: rect.top,
        bottom: rect.bottom,
      };
    }
    current = current.parentElement;
  }
  return null;
}

const web = staticServer();
const api = apiServer();
let browser;

try {
  await Promise.all([listen(web, 8773), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });

  await page.goto('http://127.0.0.1:8773', { waitUntil: 'networkidle' });
  const execution = page.getByLabel('Engineering run IMPLEMENT');
  await execution.waitFor({ state: 'attached', timeout: 10000 });
  await page.getByText('SPEC · APPROVED').waitFor({ timeout: 10000 });

  const before = await execution.evaluate(scrollGeometry);
  const composerBefore = await page.getByLabel('Message Parallax').boundingBox();
  assert(before, 'mobile governed scroll: active engineering run is not inside a vertical scroll surface');
  assert(before.scrollHeight > before.clientHeight + 80,
    `mobile governed scroll: content is not meaningfully scrollable (${before.scrollHeight} <= ${before.clientHeight})`);
  assert(composerBefore, 'mobile governed scroll: composer is not measurable');

  await execution.evaluate((node) => node.scrollIntoView({ block: 'end', behavior: 'instant' }));
  await page.waitForTimeout(120);

  const after = await execution.evaluate(scrollGeometry);
  const composerAfter = await page.getByLabel('Message Parallax').boundingBox();
  const cancelBox = await page.getByText('Cancel', { exact: true }).boundingBox();
  assert(after && after.scrollTop > 0, 'mobile governed scroll: scrolling to the execution controls did not move the content surface');
  assert(composerAfter && Math.abs(composerAfter.y - composerBefore.y) <= 2,
    `mobile governed scroll: fixed composer moved during content scroll (${composerBefore.y} -> ${composerAfter?.y})`);
  assert(cancelBox && cancelBox.y >= after.top - 2 && cancelBox.y + cancelBox.height <= after.bottom + 2,
    'mobile governed scroll: lower execution controls are not reachable inside the scroll viewport');
  assert(errors.length === 0, `mobile governed scroll: browser errors: ${errors.join(' | ')}`);

  await page.screenshot({ path: `${evidenceDir}/mobile-governed-scroll.png`, fullPage: true });
  console.log(JSON.stringify({
    viewport: { width: 390, height: 844 },
    before,
    after,
    composerBefore,
    composerAfter,
    cancelBox,
    activeRunScrollable: true,
    composerStable: true,
  }, null, 2));

  await page.close();
} finally {
  await browser?.close();
  web.close();
  api.close();
}
