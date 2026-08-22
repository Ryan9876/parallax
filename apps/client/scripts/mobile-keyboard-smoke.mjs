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
  id: '55555555-5555-4555-8555-555555555555',
  title: 'Mobile keyboard acceptance',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.13.0',
  created_at: '2026-08-22T13:47:00Z',
  updated_at: '2026-08-22T13:47:00Z',
  messages: [],
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
      json(response, 200, null, origin);
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
  await Promise.all([listen(staticSite, 8768), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });

  await page.addInitScript(() => {
    class FakeVisualViewport extends EventTarget {
      width = 390;
      height = 844;
      offsetLeft = 0;
      offsetTop = 0;
      pageLeft = 0;
      pageTop = 0;
      scale = 1;
    }
    const fake = new FakeVisualViewport();
    Object.defineProperty(window, 'visualViewport', {
      configurable: true,
      value: fake,
    });
    window.__PARALLAX_SET_TEST_VISUAL_VIEWPORT__ = (height, offsetTop = 0) => {
      fake.height = height;
      fake.offsetTop = offsetTop;
      fake.dispatchEvent(new Event('resize'));
      fake.dispatchEvent(new Event('scroll'));
    };
  });

  await page.goto('http://127.0.0.1:8768', { waitUntil: 'networkidle' });
  const input = page.getByLabel('Message Parallax');
  await input.waitFor({ timeout: 10000 });

  const fontSize = await input.evaluate((node) => parseFloat(getComputedStyle(node).fontSize));
  assert(fontSize >= 16, `mobile keyboard: editable font size must prevent iOS focus zoom, got ${fontSize}px`);

  await input.focus();
  await page.evaluate(() => window.__PARALLAX_SET_TEST_VISUAL_VIEWPORT__(480, 72));
  await page.locator('#root[data-parallax-keyboard-visible="true"]').waitFor({ timeout: 5000 });

  const rootBox = await page.locator('#root').boundingBox();
  const inputBox = await input.boundingBox();
  assert(rootBox && inputBox, 'mobile keyboard: required geometry was not measurable');
  assert(Math.abs(rootBox.y - 72) <= 2, `mobile keyboard: root did not compensate visual viewport offset (${rootBox.y}px)`);
  assert(Math.abs(rootBox.height - 480) <= 2, `mobile keyboard: root did not fit visible viewport (${rootBox.height}px)`);
  assert(inputBox.y >= rootBox.y, 'mobile keyboard: composer input moved above the visible viewport');
  assert(inputBox.y + inputBox.height <= 552, `mobile keyboard: composer remains behind keyboard (${inputBox.y + inputBox.height} > 552)`);

  await page.screenshot({ path: `${evidenceDir}/mobile-keyboard-visible.png` });

  await page.evaluate(() => window.__PARALLAX_SET_TEST_VISUAL_VIEWPORT__(844, 0));
  await page.waitForFunction(() => !document.getElementById('root')?.dataset.parallaxKeyboardVisible);
  const restored = await page.locator('#root').boundingBox();
  assert(restored && Math.abs(restored.y) <= 2, `mobile keyboard: root offset was not restored (${restored?.y}px)`);
  assert(restored && Math.abs(restored.height - 844) <= 2, `mobile keyboard: root height was not restored (${restored?.height}px)`);
  assert(errors.length === 0, `mobile keyboard: browser errors: ${errors.join(' | ')}`);

  console.log(JSON.stringify({
    viewport: { width: 390, layoutHeight: 844 },
    simulatedVisualViewport: { height: 480, offsetTop: 72 },
    fontSize,
    rootBox,
    inputBox,
    restored,
    composerVisibleAboveKeyboard: true,
    focusZoomPrevented: true,
    viewportRestored: true,
  }, null, 2));

  await page.close();
} finally {
  await browser?.close();
  staticSite.close();
  api.close();
}
