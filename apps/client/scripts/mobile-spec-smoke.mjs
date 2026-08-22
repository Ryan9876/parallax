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
  '.json': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

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
  id: '33333333-3333-4333-8333-333333333333',
  title: 'Add a Simple About Page',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.13.0',
  created_at: '2026-08-22T12:00:00Z',
  updated_at: '2026-08-22T12:00:00Z',
  messages: [
    {
      id: 'mobile-user-1',
      role: 'user',
      content: 'Add a simple accessible About page and keep the existing application styling.',
      status: 'complete',
      created_at: '2026-08-22T12:00:00Z',
    },
  ],
};

const workSpecification = {
  id: '44444444-4444-4444-8444-444444444444',
  conversation_id: conversation.id,
  revision: 3,
  status: 'DRAFT',
  title: 'Add a Simple About Page',
  objective: 'Add a simple, accessible About page to the application and make it reachable through the application existing navigation or routing structure.',
  constraints: [
    'Use the application existing UI patterns, navigation, and styling conventions where applicable.',
    'Keep the page simple and limited to the functionality described.',
    'Do not invent organization, product, contact, or legal metadata that has not been supplied.',
    'Preserve current application behavior outside the About page change.',
  ],
  acceptance_criteria: [
    'An About page is available at a distinct application route or navigation destination.',
    'Users can reach the About page through the application existing navigation structure, where such navigation exists.',
    'The page renders successfully without console errors or broken links.',
    'The page uses the application existing visual styling and is usable on supported screen sizes.',
    'The About page content and required metadata are confirmed before final implementation.',
  ],
  risks: [
    'A mobile implementation could crowd the conversation workspace if the specification review surface is not bounded.',
    'An oversized governed surface could obscure the persistent composer.',
  ],
  open_questions: ['What exact About page metadata should be displayed?'],
  confidence: 0.93,
  program_version: 'mobile-spec-smoke',
  model_id: 'test-model',
  created_at: '2026-08-22T12:00:00Z',
  updated_at: '2026-08-22T12:00:00Z',
  approved_at: null,
};

function apiServer() {
  function cors(response, origin) {
    response.setHeader('access-control-allow-origin', origin ?? '*');
    response.setHeader('access-control-allow-headers', 'Content-Type,Accept');
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
    if (pathname === '/v1/conversations' && request.method === 'GET') {
      json(response, 200, [conversation], origin);
      return;
    }
    if (pathname === `/v1/conversations/${conversation.id}` && request.method === 'GET') {
      json(response, 200, conversation, origin);
      return;
    }
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/latest` && request.method === 'GET') {
      json(response, 200, workSpecification, origin);
      return;
    }
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/approved` && request.method === 'GET') {
      json(response, 200, null, origin);
      return;
    }
    if (pathname === `/v1/engineering-runs/conversation/${conversation.id}/latest` && request.method === 'GET') {
      json(response, 200, null, origin);
      return;
    }
    json(response, 404, { detail: 'not found' }, origin);
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
  await page.getByText('SPEC · DRAFT').waitFor({ timeout: 10000 });
  await page.getByLabel('Expand work specification').click();
  await page.getByLabel('Work specification details').waitFor({ timeout: 5000 });

  const specBox = await page.getByLabel('Work specification', { exact: true }).boundingBox();
  const detailsBox = await page.getByLabel('Work specification details').boundingBox();
  const inputBox = await page.getByLabel('Message Parallax').boundingBox();
  const approveBox = await page.getByLabel('Approve work specification').boundingBox();
  const refreshBox = await page.getByLabel('Refresh work specification draft').boundingBox();
  const collapseBox = await page.getByLabel('Collapse work specification').boundingBox();
  const detailScroll = await page.getByLabel('Work specification details').evaluate((node) => ({
    clientHeight: node.clientHeight,
    scrollHeight: node.scrollHeight,
    overflowY: getComputedStyle(node).overflowY,
  }));

  assert(specBox && detailsBox && inputBox, 'mobile spec: required geometry was not measurable');
  assert(specBox.y + specBox.height <= inputBox.y - 8, `mobile spec: specification overlaps composer (${specBox.y + specBox.height} > ${inputBox.y - 8})`);
  assert(specBox.height <= 540, `mobile spec: expanded specification is too tall (${specBox.height}px)`);
  assert(detailScroll.scrollHeight > detailScroll.clientHeight + 24, 'mobile spec: long specification details are not internally scrollable');
  assert(['auto', 'scroll'].includes(detailScroll.overflowY), `mobile spec: expected scrollable detail overflow, got ${detailScroll.overflowY}`);

  for (const [name, box] of [['approve', approveBox], ['refresh', refreshBox], ['collapse', collapseBox]]) {
    assert(box && box.height >= 44, `mobile spec: ${name} target is smaller than 44px`);
  }
  assert(!boxesOverlap(approveBox, refreshBox), 'mobile spec: approve and refresh controls overlap');
  assert(!boxesOverlap(refreshBox, collapseBox), 'mobile spec: refresh and disclosure controls overlap');
  assert(!boxesOverlap(approveBox, collapseBox), 'mobile spec: approve and disclosure controls overlap');
  assert(errors.length === 0, `mobile spec: browser errors: ${errors.join(' | ')}`);

  await page.screenshot({ path: `${evidenceDir}/mobile-spec-expanded.png` });
  console.log(JSON.stringify({
    viewport: { width: 390, height: 844 },
    specBox,
    detailsBox,
    inputBox,
    detailScroll,
    controls: { approveBox, refreshBox, collapseBox },
    nonOverlapping: true,
    internallyScrollable: true,
  }, null, 2));

  await page.close();
} finally {
  await browser?.close();
  staticSite.close();
  api.close();
}
