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
  id: '77777777-7777-4777-8777-777777777777',
  title: 'Simple About Page',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.13.0',
  created_at: '2026-08-22T14:00:00Z',
  updated_at: '2026-08-22T14:00:00Z',
  messages: [
    {
      id: 'clearance-user',
      role: 'user',
      content: 'Add a simple About page to this application.',
      status: 'complete',
      created_at: '2026-08-22T14:00:00Z',
    },
    {
      id: 'clearance-assistant',
      role: 'assistant',
      content: 'This request materially changes the approved objective. An approved specification amendment is required before implementation proceeds.',
      status: 'complete',
      created_at: '2026-08-22T14:00:05Z',
    },
  ],
};

const workSpecification = {
  id: '88888888-8888-4888-8888-888888888888',
  conversation_id: conversation.id,
  revision: 4,
  status: 'DRAFT',
  title: 'Simple About Page',
  objective: 'Add a simple, accessible About page to the application and make it reachable through the existing navigation or routing structure.',
  constraints: [
    'The page should remain simple and focused on introducing the application.',
    'An approved specification amendment is required before implementation proceeds against this changed objective.',
    'Preserve current application behavior outside the About page change.',
  ],
  acceptance_criteria: [
    'The page follows the application existing layout and styling conventions.',
    'The page is usable with standard keyboard navigation and has an informative page title.',
    'The page renders without console errors or broken links.',
  ],
  risks: ['A fixed composer must never obscure the newest response.'],
  open_questions: ['What exact About page metadata should be displayed?'],
  confidence: 0.94,
  program_version: 'composer-clearance-smoke',
  model_id: 'test-model',
  created_at: '2026-08-22T14:00:10Z',
  updated_at: '2026-08-22T14:00:10Z',
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
  const response = page.getByLabel('Parallax response').last();
  await response.waitFor({ timeout: 5000 });

  await response.evaluate((node) => {
    let current = node.parentElement;
    while (current) {
      const style = getComputedStyle(current);
      if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && current.scrollHeight > current.clientHeight) {
        current.scrollTop = current.scrollHeight;
        return;
      }
      current = current.parentElement;
    }
  });
  await page.waitForTimeout(80);

  const responseBox = await response.boundingBox();
  const inputBox = await page.getByLabel('Message Parallax').boundingBox();
  const specBox = await page.getByLabel('Work specification', { exact: true }).boundingBox();

  assert(responseBox && inputBox && specBox, 'composer clearance: required geometry was not measurable');
  assert(responseBox.y + responseBox.height <= inputBox.y - 8,
    `composer clearance: newest response intersects composer (${responseBox.y + responseBox.height} > ${inputBox.y - 8})`);
  assert(specBox.y + specBox.height <= inputBox.y - 8,
    `composer clearance: specification intersects composer (${specBox.y + specBox.height} > ${inputBox.y - 8})`);
  assert(errors.length === 0, `composer clearance: browser errors: ${errors.join(' | ')}`);

  await page.screenshot({ path: `${evidenceDir}/mobile-composer-clearance.png` });
  console.log(JSON.stringify({
    viewport: { width: 390, height: 844 },
    specBox,
    responseBox,
    inputBox,
    responseClearance: inputBox.y - (responseBox.y + responseBox.height),
    specificationClearance: inputBox.y - (specBox.y + specBox.height),
    nonOverlapping: true,
  }, null, 2));

  await page.close();
} finally {
  await browser?.close();
  staticSite.close();
  api.close();
}
