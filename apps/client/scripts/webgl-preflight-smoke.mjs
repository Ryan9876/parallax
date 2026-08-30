import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
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

const server = createServer((request, response) => {
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

const conversation = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  title: 'WebGL preflight acceptance',
  mode: 'reason',
  status: 'ACTIVE',
  spec_id: 'P2-V0.23.16',
  created_at: '2026-08-30T23:00:00Z',
  updated_at: '2026-08-30T23:00:00Z',
  messages: [],
};

let browser;
try {
  await listen(server, 8767);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  const requestedPaths = [];

  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('request', (request) => requestedPaths.push(new URL(request.url()).pathname));

  await page.route('**/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const cors = {
      'access-control-allow-origin': '*',
      'access-control-allow-headers': 'Content-Type,Accept,X-Parallax-Session',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
    };
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: cors, body: '' });
      return;
    }
    if (url.pathname === '/v1/conversations' && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', headers: cors, body: JSON.stringify([conversation]) });
      return;
    }
    if (url.pathname === '/v1/projects' && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', headers: cors, body: '[]' });
      return;
    }
    await route.fulfill({ status: 404, contentType: 'application/json', headers: cors, body: JSON.stringify({ detail: 'not found' }) });
  });

  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function getContext(type, ...args) {
      const normalized = String(type).toLowerCase();
      if (normalized === 'webgl' || normalized === 'webgl2' || normalized === 'experimental-webgl') return null;
      return original.call(this, type, ...args);
    };
  });

  await page.goto('http://127.0.0.1:8767', { waitUntil: 'networkidle' });
  await page.getByText(/Reduced graphics mode/).first().waitFor({ timeout: 10000 });
  await page.getByText('A simpler display is active.').waitFor({ timeout: 10000 });
  await page.getByLabel('Message Parallax').waitFor({ timeout: 10000 });

  const canvasCount = await page.locator('canvas').count();
  assert(canvasCount === 0, `WebGL-unavailable startup mounted ${canvasCount} canvas element(s)`);
  assert(!requestedPaths.includes('/canvaskit.wasm'), 'WebGL-unavailable startup requested CanvasKit WASM before choosing reduced graphics');
  assert(errors.length === 0, `WebGL-unavailable startup emitted browser errors: ${errors.join(' | ')}`);

  console.log(JSON.stringify({
    spec: 'P2-V0.23.16',
    webglUnavailableFallback: true,
    canvaskitRequested: false,
    canvasCount,
    browserErrors: 0,
  }, null, 2));

  await page.close();
} finally {
  await browser?.close();
  server.close();
}
