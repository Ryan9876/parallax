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
  title: 'Add a Simple About Page',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.18.7',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: '2026-08-26T12:00:00Z',
  updated_at: '2026-08-26T12:00:00Z',
  messages: [
    {
      id: 'mobile-user-1',
      role: 'user',
      content: 'Add a simple accessible About page and keep the existing application styling.',
      status: 'complete',
      created_at: '2026-08-26T12:00:00Z',
    },
  ],
};

let workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 3,
  status: 'DRAFT',
  title: 'Add a Simple About Page',
  objective: 'Add a simple, accessible About page to the application and make it reachable through the existing navigation or routing structure.',
  constraints: [
    'Use the existing UI patterns, navigation, and styling conventions where applicable.',
    'Keep the page simple and limited to the functionality described.',
    'Preserve current application behavior outside the About page change.',
  ],
  acceptance_criteria: [
    'An About page is available at a distinct application route or navigation destination.',
    'Users can reach the About page through the existing navigation structure.',
    'The page renders successfully without console errors or broken links.',
    'The page uses the existing visual styling and is usable on supported screen sizes.',
    'The About page content and required metadata are confirmed before final implementation.',
  ],
  risks: ['A mobile implementation could crowd the conversation workspace if specification review remains inline.'],
  open_questions: ['What exact About page metadata should be displayed?'],
  confidence: 0.93,
  program_version: 'mobile-spec-smoke',
  model_id: 'test-model',
  created_at: '2026-08-26T12:00:00Z',
  updated_at: '2026-08-26T12:00:00Z',
  approved_at: null,
};

function apiServer() {
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
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') {
      return json(response, 200, workSpecification.status === 'APPROVED' ? workSpecification : null, origin);
    }
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, null, origin);
    if (pathname === `/v1/work-specifications/${SPEC_ID}/approve` && request.method === 'POST') {
      const now = new Date().toISOString();
      workSpecification = { ...workSpecification, status: 'APPROVED', approved_at: now, updated_at: now };
      return json(response, 200, workSpecification, origin);
    }
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

function boxesOverlap(a, b) {
  return a.x < b.x + b.width
    && a.x + a.width > b.x
    && a.y < b.y + b.height
    && a.y + a.height > b.y;
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
  await page.getByLabel('Review specification').waitFor({ timeout: 10000 });

  const nav = page.getByTestId('mobile-bottom-navigation');
  const navBox = await nav.boundingBox();
  const inputBox = await page.getByLabel('Message Parallax').boundingBox();
  assert(navBox && inputBox, 'mobile spec: mobile navigation or composer geometry was not measurable');
  assert(inputBox.y + inputBox.height <= navBox.y + 1, 'mobile spec: composer overlaps the bottom navigation');
  assert(await page.getByLabel('Work specification').count() === 0, 'mobile spec: legacy inline Work Specification should not render in Chat');
  assert(await page.getByRole('tab').count() === 3, 'mobile spec: primary navigation must expose exactly Chat, Build, and Project');

  await page.getByLabel('Review specification').click();
  await page.getByTestId('mobile-specification-detail').waitFor({ timeout: 5000 });
  await page.getByText('Review before building', { exact: true }).waitFor();
  await page.getByText('ACCEPTANCE CRITERIA', { exact: true }).waitFor();
  await page.getByText('OPEN QUESTIONS', { exact: true }).waitFor();
  await page.getByText('RISKS', { exact: true }).waitFor();

  const detailRoot = await page.getByTestId('mobile-specification-detail').boundingBox();
  const approveBox = await page.getByLabel('Approve and continue').boundingBox();
  const refreshBox = await page.getByLabel('Refresh specification draft').boundingBox();
  const backBox = await page.getByLabel('Back to Chat').boundingBox();
  assert(detailRoot && approveBox && refreshBox && backBox, 'mobile spec: dedicated detail controls were not measurable');
  for (const [name, box] of [['approve', approveBox], ['refresh', refreshBox], ['back', backBox]]) {
    assert(box.height >= 44, `mobile spec: ${name} target is smaller than 44px`);
  }
  assert(!boxesOverlap(approveBox, refreshBox), 'mobile spec: approve and refresh controls overlap');
  assert(await page.getByLabel('Message Parallax').count() === 0, 'mobile spec: composer should not compete with the full-screen specification review');

  await page.screenshot({ path: `${evidenceDir}/mobile-specification-review.png`, fullPage: true });
  await page.getByLabel('Approve and continue').click();
  await page.waitForTimeout(250);
  await page.getByText('Approved build', { exact: true }).waitFor({ timeout: 5000 });
  assert(errors.length === 0, `mobile spec: browser errors: ${errors.join(' | ')}`);

  console.log(JSON.stringify({
    viewport: { width: 390, height: 844 },
    bottomNavigation: ['Chat', 'Build', 'Project'],
    inlineLegacySpecification: false,
    dedicatedReview: true,
    approvalSucceeded: true,
    controls: { approveBox, refreshBox, backBox },
    composerClearOfNavigation: true,
  }, null, 2));

  await page.close();
} finally {
  await browser?.close();
  staticSite.close();
  api.close();
}
