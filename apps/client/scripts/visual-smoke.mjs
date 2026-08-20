import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';
import { createHash } from 'node:crypto';

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

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

function staticServer({ failSkia = false } = {}) {
  return createServer((request, response) => {
    const rawPath = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (failSkia && rawPath === '/canvaskit.wasm') {
      response.writeHead(503, { 'content-type': 'text/plain' });
      response.end('CanvasKit intentionally unavailable for AC-10 validation');
      return;
    }
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

const mockStreamState = {
  open: false,
  chunksSent: 0,
  completed: false,
};

function apiServer() {
  let conversation = null;
  const answer = 'The response is being inscribed line by line. The optical head should follow the active wrapped line, leave a short cool-blue energized edge on fresh glyphs, and then cool into normal selectable text without disturbing the calm surface behind it.';

  function baseConversation(mode = 'reason') {
    return {
      id: '11111111-1111-4111-8111-111111111111',
      title: 'New conversation',
      mode,
      status: 'ACTIVE',
      spec_id: 'P2-V0.1.0',
      created_at: '2026-08-20T08:00:00Z',
      updated_at: '2026-08-20T08:00:00Z',
      messages: [],
    };
  }

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

  async function requestJson(request) {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    if (!chunks.length) return {};
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  }

  async function sse(response, name, data, waitMs = 0) {
    if (waitMs) await delay(waitMs);
    response.write(`event: ${name}\ndata: ${JSON.stringify(data)}\n\n`);
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
    if (pathname === '/v1/conversations' && request.method === 'GET') {
      json(response, 200, conversation ? [conversation] : [], origin);
      return;
    }
    if (pathname === '/v1/conversations' && request.method === 'POST') {
      const payload = await requestJson(request);
      conversation = baseConversation(payload.mode === 'code' ? 'code' : 'reason');
      json(response, 200, conversation, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+$/.test(pathname) && request.method === 'GET') {
      json(response, conversation ? 200 : 404, conversation ?? { detail: 'Conversation not found' }, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/responses$/.test(pathname) && request.method === 'POST') {
      const payload = await requestJson(request);
      if (!conversation) conversation = baseConversation('reason');
      const now = new Date().toISOString();
      conversation.title = String(payload.content ?? '').slice(0, 72) || 'New conversation';
      conversation.updated_at = now;

      mockStreamState.open = true;
      mockStreamState.chunksSent = 0;
      mockStreamState.completed = false;

      cors(response, origin);
      response.writeHead(200, {
        'content-type': 'text/event-stream',
        'cache-control': 'no-cache',
        connection: 'keep-alive',
      });
      response.flushHeaders?.();

      const userMessage = {
        id: `u-${conversation.messages.length}`,
        role: 'user',
        content: String(payload.content ?? ''),
        status: 'complete',
        created_at: now,
      };
      const assistantMessage = {
        id: `a-${conversation.messages.length + 1}`,
        role: 'assistant',
        content: answer,
        status: 'complete',
        created_at: now,
      };
      const splitA = Math.floor(answer.length * 0.34);
      const splitB = Math.floor(answer.length * 0.68);

      await sse(response, 'state', { phase: 'THINKING' });
      await sse(response, 'state', { phase: 'RESPONDING' }, 180);
      await sse(response, 'chunk', { text: answer.slice(0, splitA) }, 120);
      mockStreamState.chunksSent = 1;
      await sse(response, 'chunk', { text: answer.slice(splitA, splitB) }, 900);
      mockStreamState.chunksSent = 2;
      await sse(response, 'chunk', { text: answer.slice(splitB) }, 900);
      mockStreamState.chunksSent = 3;
      await sse(response, 'state', { phase: 'VERIFYING' }, 180);

      conversation.messages = [...conversation.messages, userMessage, assistantMessage];
      await sse(response, 'complete', {
        phase: 'COMPLETE',
        message_id: assistantMessage.id,
        confidence: 0.94,
        trace: { spec_id: 'P2-V0.1.0' },
      }, 120);
      mockStreamState.completed = true;
      response.end();
      mockStreamState.open = false;
      return;
    }
    json(response, 404, { detail: 'not found' }, origin);
  });
}

function hash(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

async function inspectViewport(browser, name, width, height, report) {
  const page = await browser.newPage({ viewport: { width, height } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });

  await page.goto('http://127.0.0.1:8765', { waitUntil: 'networkidle' });
  await page.getByLabel('Message Parallax').waitFor();
  await page.waitForTimeout(500);

  const first = await page.screenshot({ path: `${evidenceDir}/${name}-idle-a.png` });
  await page.waitForTimeout(700);
  const second = await page.screenshot({ path: `${evidenceDir}/${name}-idle-b.png` });
  const geometry = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
    canvasCount: document.querySelectorAll('canvas').length,
  }));
  const composerBox = await page.getByLabel('Message Parallax').boundingBox();

  assert(geometry.scrollWidth <= geometry.clientWidth + 1, `${name}: horizontal overflow ${geometry.scrollWidth} > ${geometry.clientWidth}`);
  assert(composerBox && composerBox.x >= 0 && composerBox.x + composerBox.width <= width + 1, `${name}: composer is clipped horizontally`);
  assert(geometry.canvasCount > 0, `${name}: Skia canvases did not initialize`);
  assert(hash(first) !== hash(second), `${name}: living surface/logo frames did not change over time`);
  assert(errors.length === 0, `${name}: browser errors: ${errors.join(' | ')}`);

  report.viewports.push({ name, width, height, ...geometry, composerBox, animatedFrameChanged: true });

  if (name === 'desktop') {
    const idleCanvasCount = geometry.canvasCount;
    await page.getByLabel('Message Parallax').fill('Show the optical printing behavior on a wrapped response.');
    await page.getByLabel('Send message').click();
    await page.getByText('Optical renderer active').waitFor({ timeout: 5000 });
    await page.waitForFunction(() => document.body.innerText.includes('The response is being'), null, { timeout: 5000 });

    assert(mockStreamState.open, 'desktop: mock SSE stream was already closed when live optical inscription was observed');
    assert(mockStreamState.chunksSent >= 1 && mockStreamState.chunksSent < 3, `desktop: expected an intermediate streamed chunk, observed ${mockStreamState.chunksSent}`);
    await page.screenshot({ path: `${evidenceDir}/desktop-responding-early.png` });

    await page.waitForTimeout(650);
    await page.screenshot({ path: `${evidenceDir}/desktop-responding-mid.png` });
    const respondingCanvasCount = await page.locator('canvas').count();
    const hotGlyphCount = await page.locator('span').evaluateAll((nodes) => nodes.filter((node) => getComputedStyle(node).textShadow !== 'none').length);
    assert(respondingCanvasCount > idleCanvasCount, `desktop: optical head canvas did not appear (${respondingCanvasCount} <= ${idleCanvasCount})`);
    assert(hotGlyphCount > 0, 'desktop: no energized fresh-glyph text shadow detected while responding');

    await page.getByText(/Parallax 2\.0 · complete/i).waitFor({ timeout: 10000 });
    await page.getByText(/The response is being inscribed line by line/).first().waitFor();
    await page.screenshot({ path: `${evidenceDir}/desktop-complete.png` });
    assert(mockStreamState.completed && !mockStreamState.open, 'desktop: mock SSE stream did not complete cleanly');
    report.opticalTypesetter = {
      idleCanvasCount,
      respondingCanvasCount,
      hotGlyphCount,
      liveChunkObservedBeforeStreamCompletion: true,
      completed: true,
    };
  }

  await page.close();
}

async function inspectFallback(browser, report) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  await page.goto('http://127.0.0.1:8766', { waitUntil: 'networkidle' });
  await page.getByLabel('Message Parallax').waitFor({ timeout: 10000 });
  await page.getByText(/Reduced graphics mode/).first().waitFor();
  const canvasCount = await page.locator('canvas').count();
  assert(canvasCount === 0, `fallback: expected zero Skia canvases, found ${canvasCount}`);

  await page.getByLabel('Message Parallax').fill('Continue without Skia.');
  await page.getByLabel('Send message').click();
  await page.getByText(/The response is being inscribed line by line/).first().waitFor({ timeout: 10000 });
  await page.screenshot({ path: `${evidenceDir}/fallback-functional.png` });

  // AC-10 has two distinct claims: normal text is usable without Skia, and the
  // request lifecycle still completes. Wait for the reduced-graphics product
  // state before asserting transport closure instead of racing the stream.
  await page.getByText(/Reduced graphics mode · complete/i).waitFor({ timeout: 10000 });
  assert(mockStreamState.completed && !mockStreamState.open, 'fallback: conversation stream did not complete cleanly without Skia');

  const expectedSkiaFailure = (entry) => [
    'Skia failed to initialize',
    '503 (Service Unavailable)',
    'wasm streaming compile failed',
    'falling back to ArrayBuffer instantiation',
    'failed to asynchronously prepare wasm',
    'both async and sync fetching of the wasm failed',
    'Aborted(both async and sync fetching of the wasm failed)',
  ].some((pattern) => entry.includes(pattern));
  const unexpected = errors.filter((entry) => !expectedSkiaFailure(entry));
  assert(unexpected.length === 0, `fallback: unexpected browser errors: ${unexpected.join(' | ')}`);
  assert(errors.some(expectedSkiaFailure), 'fallback: CanvasKit outage did not produce the expected initialization failure evidence');
  report.fallback = {
    canvasCount,
    functionalConversation: true,
    expectedSkiaInitializationErrorObserved: true,
    observedExpectedErrorCount: errors.filter(expectedSkiaFailure).length,
  };
  await page.close();
}

const normal = staticServer();
const fallback = staticServer({ failSkia: true });
const api = apiServer();
const report = { specId: 'P2-V0.1.0', viewports: [], opticalTypesetter: null, fallback: null };
let browser;

try {
  await Promise.all([listen(normal, 8765), listen(fallback, 8766), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  await inspectViewport(browser, 'mobile', 390, 844, report);
  await inspectViewport(browser, 'tablet', 768, 1024, report);
  await inspectViewport(browser, 'desktop', 1440, 900, report);
  await inspectFallback(browser, report);
  writeFileSync(`${evidenceDir}/report.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser?.close();
  normal.close();
  fallback.close();
  api.close();
}
