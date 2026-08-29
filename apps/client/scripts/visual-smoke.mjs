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

const amendmentMessage = 'Your request is different from the plan you approved. Parallax stopped before changing that approved work. Continue the approved work, or start a new goal for the new request.';

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
  amendment: false,
};

function apiServer() {
  let conversation = null;
  let workSpecification = null;
  const answer = 'The response streams into the warm editorial workspace as normal selectable text. A restrained live trace may mark current output without delaying content or implying progress beyond server evidence.';

  function baseConversation(mode = 'reason') {
    return {
      id: '11111111-1111-4111-8111-111111111111',
      title: 'New conversation',
      mode,
      status: 'ACTIVE',
      spec_id: 'P2-V0.5.0',
      created_at: '2026-08-20T08:00:00Z',
      updated_at: '2026-08-20T08:00:00Z',
      messages: [],
    };
  }

  function baseWorkSpecification() {
    const now = new Date().toISOString();
    return {
      id: '22222222-2222-4222-8222-222222222222',
      conversation_id: conversation?.id ?? '11111111-1111-4111-8111-111111111111',
      revision: (workSpecification?.revision ?? 0) + 1,
      status: 'DRAFT',
      title: 'Warm editorial response behavior',
      objective: 'Preserve the calm Parallax conversation while verifying durable specification capture and warm editorial live-response behavior.',
      constraints: ['Keep conversation as the primary product surface.'],
      acceptance_criteria: [
        'The work specification persists as a durable draft.',
        'The operator explicitly approves the specification before it is treated as approved.',
      ],
      risks: ['Shell chrome could compete with the conversation.'],
      open_questions: [],
      confidence: 0.94,
      program_version: 'work-spec-v0.7.0',
      model_id: 'visual-smoke-model',
      created_at: now,
      updated_at: now,
      approved_at: null,
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
      workSpecification = null;
      json(response, 200, conversation, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+$/.test(pathname) && request.method === 'GET') {
      json(response, conversation ? 200 : 404, conversation ?? { detail: 'Conversation not found' }, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/latest$/.test(pathname) && request.method === 'GET') {
      json(response, 200, workSpecification, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/draft$/.test(pathname) && request.method === 'POST') {
      workSpecification = baseWorkSpecification();
      json(response, 200, workSpecification, origin);
      return;
    }
    if (/^\/v1\/work-specifications\/[^/]+\/approve$/.test(pathname) && request.method === 'POST') {
      if (!workSpecification) {
        json(response, 404, { detail: 'Work specification not found' }, origin);
        return;
      }
      const now = new Date().toISOString();
      workSpecification = { ...workSpecification, status: 'APPROVED', approved_at: now, updated_at: now };
      json(response, 200, workSpecification, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/responses$/.test(pathname) && request.method === 'POST') {
      const payload = await requestJson(request);
      if (!conversation) conversation = baseConversation('reason');
      const now = new Date().toISOString();
      const content = String(payload.content ?? '');
      conversation.title = content.slice(0, 72) || 'New conversation';
      conversation.updated_at = now;

      mockStreamState.open = true;
      mockStreamState.chunksSent = 0;
      mockStreamState.completed = false;
      mockStreamState.amendment = false;

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
        content,
        status: 'complete',
        created_at: now,
      };

      if (content.includes('Replace the approved objective entirely')) {
        const assistantMessage = {
          id: `a-${conversation.messages.length + 1}`,
          role: 'assistant',
          content: amendmentMessage,
          status: 'complete',
          created_at: now,
        };
        conversation.status = 'SPEC_AMENDMENT';
        conversation.messages = [...conversation.messages, userMessage, assistantMessage];
        await sse(response, 'state', { phase: 'THINKING' });
        await sse(response, 'state', { phase: 'SPEC_AMENDMENT' }, 100);
        await sse(response, 'amendment', {
          phase: 'SPEC_AMENDMENT',
          message_id: assistantMessage.id,
          text: amendmentMessage,
          confidence: 0.96,
          scope_decision: 'SPEC_AMENDMENT',
          trace: { spec_id: 'P2-V0.5.0', final_state: 'SPEC_AMENDMENT' },
        }, 80);
        mockStreamState.amendment = true;
        mockStreamState.completed = true;
        response.end();
        mockStreamState.open = false;
        return;
      }

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

      conversation.status = 'ACTIVE';
      conversation.messages = [...conversation.messages, userMessage, assistantMessage];
      await sse(response, 'complete', {
        phase: 'COMPLETE',
        message_id: assistantMessage.id,
        confidence: 0.94,
        scope_decision: 'CONTINUE',
        trace: { spec_id: 'P2-V0.5.0' },
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

  const logoCount = await page.getByLabel('Parallax orbital planet mark').count();
  assert(logoCount > 0, `${name}: approved orbital identity was not rendered`);

  const navCount = await page.getByTestId('editorial-navigation-rail').count();
  const utilityCount = await page.getByTestId('editorial-utility-rail').count();
  if (name === 'mobile') {
    assert(navCount === 0, 'mobile: desktop navigation rail must reflow away');
    assert(utilityCount === 0, 'mobile: utility rail must reflow away');
  } else if (name === 'tablet') {
    assert(navCount === 1, 'tablet: navigation rail should remain available at 768px');
    assert(utilityCount === 0, 'tablet: desktop utility rail must not compress the workplane');
  } else if (name === 'desktop') {
    assert(navCount === 1, 'desktop: warm editorial navigation rail missing');
    assert(utilityCount === 1, 'desktop: warm editorial utility rail missing');
    await page.getByText('What shall we build today?').waitFor();
    const railStyle = await page.getByTestId('editorial-navigation-rail').evaluate((node) => getComputedStyle(node).backgroundColor);
    assert(!railStyle.includes('139, 156, 255') && !railStyle.includes('209, 139, 255'), `desktop: legacy violet rail detected (${railStyle})`);
  }

  const first = await page.screenshot({ path: `${evidenceDir}/${name}-idle-a.png` });
  await page.waitForTimeout(1100);
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

  report.viewports.push({ name, width, height, ...geometry, composerBox, logoCount, animatedFrameChanged: true });

  if (name === 'desktop') {
    const idleCanvasCount = geometry.canvasCount;
    await page.getByLabel('Message Parallax').fill('Show the live response behavior on a wrapped response.');
    await page.getByLabel('Send message').click();
    await page.getByText('Live response').waitFor({ timeout: 5000 });
    await page.waitForFunction(() => document.body.innerText.includes('The response streams into the warm editorial workspace'), null, { timeout: 5000 });

    assert(mockStreamState.open, 'desktop: mock SSE stream was already closed when live response was observed');
    assert(mockStreamState.chunksSent >= 1 && mockStreamState.chunksSent < 3, `desktop: expected an intermediate streamed chunk, observed ${mockStreamState.chunksSent}`);

    const headCount = await page.getByLabel('Live response trace').count();
    assert(headCount > 0, 'desktop: compact live response trace was not rendered');
    const responseBox = await page.getByLabel('Parallax response').last().boundingBox();
    const inputBox = await page.getByLabel('Message Parallax').boundingBox();
    assert(responseBox && inputBox && responseBox.y < inputBox.y, 'desktop: response start was not automatically brought above the composer');
    const viewportBottomGuard = inputBox.y + 2;
    assert(responseBox.y < viewportBottomGuard, 'desktop: active response is hidden behind composer');

    await page.screenshot({ path: `${evidenceDir}/desktop-responding-early.png` });
    await page.waitForTimeout(650);
    await page.screenshot({ path: `${evidenceDir}/desktop-responding-mid.png` });
    const respondingCanvasCount = await page.locator('canvas').count();
    assert(respondingCanvasCount >= idleCanvasCount, `desktop: responding state lost a required canvas (${respondingCanvasCount} < ${idleCanvasCount})`);

    await page.getByText(/ask · ready/i).waitFor({ timeout: 10000 });
    await page.getByText(/The response streams into the warm editorial workspace/).first().waitFor();
    assert(mockStreamState.completed && !mockStreamState.open, 'desktop: mock SSE stream did not complete cleanly');

    await page.getByLabel('Create build plan').waitFor({ timeout: 5000 });
    await page.getByLabel('Create build plan').click();
    await page.getByText('Ready for your review').waitFor({ timeout: 5000 });
    const planSurface = page.getByLabel('Build plan', { exact: true });
    const planStyle = await planSurface.evaluate((node) => {
      const style = getComputedStyle(node);
      return {
        borderLeftWidth: parseFloat(style.borderLeftWidth || '0'),
        borderRadius: parseFloat(style.borderTopLeftRadius || '0'),
        backgroundColor: style.backgroundColor,
      };
    });
    assert(planStyle.borderLeftWidth <= 1, `desktop: Build plan retained a heavy left rule (${planStyle.borderLeftWidth}px)`);
    assert(planStyle.borderRadius >= 14, `desktop: Build plan is not using rounded editorial material (${planStyle.borderRadius}px)`);
    await page.getByLabel('Show build plan details').first().click();
    await page.getByText('The work specification persists as a durable draft.').waitFor({ timeout: 5000 });
    await page.getByLabel('Approve build plan').click();
    await page.getByText('Plan approved').waitFor({ timeout: 5000 });
    await page.screenshot({ path: `${evidenceDir}/desktop-plan-approved.png` });

    report.liveResponseTreatment = {
      idleCanvasCount,
      respondingCanvasCount,
      liveTraceRendered: true,
      streamedTextVisibleImmediately: true,
      responseFollowedAboveComposer: true,
      liveChunkObservedBeforeStreamCompletion: true,
      completed: true,
    };
    report.buildPlan = {
      created: true,
      roundedEditorialMaterial: true,
      heavyLeftRuleRemoved: true,
      expanded: true,
      operatorApproved: true,
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
  await page.getByText('Plan approved').waitFor({ timeout: 5000 });
  const canvasCount = await page.locator('canvas').count();
  assert(canvasCount === 0, `fallback: expected zero Skia canvases, found ${canvasCount}`);

  await page.getByLabel('Message Parallax').fill('Continue in the simpler display.');
  await page.getByLabel('Send message').click();
  await page.getByText(/The response streams into the warm editorial workspace/).first().waitFor({ timeout: 10000 });
  await page.screenshot({ path: `${evidenceDir}/fallback-functional.png` });

  await page.getByText(/Reduced graphics mode · ready/i).waitFor({ timeout: 10000 });
  assert(mockStreamState.completed && !mockStreamState.open, 'fallback: conversation stream did not complete cleanly without Skia');

  await page.getByLabel('Message Parallax').fill('Replace the approved objective entirely.');
  await page.getByLabel('Send message').click();
  await page.getByText(amendmentMessage).first().waitFor({ timeout: 10000 });
  await page.getByText(/Reduced graphics mode · request changed/i).waitFor({ timeout: 10000 });
  const amendmentCanvasCount = await page.locator('canvas').count();
  assert(amendmentCanvasCount === 0, `fallback amendment: expected zero Skia canvases, found ${amendmentCanvasCount}`);
  assert(mockStreamState.amendment && mockStreamState.completed && !mockStreamState.open, 'fallback amendment: amendment stream did not complete cleanly');
  await page.screenshot({ path: `${evidenceDir}/fallback-amendment.png` });

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
    buildPlanParity: true,
    amendmentStatePreservedWithoutSkia: true,
    plainLanguageStatus: true,
    expectedSkiaInitializationErrorObserved: true,
    observedExpectedErrorCount: errors.filter(expectedSkiaFailure).length,
  };
  await page.close();
}

async function inspectWebGlPreflight(report) {
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-webgl', '--disable-software-rasterizer'],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  await page.goto('http://127.0.0.1:8765', { waitUntil: 'networkidle' });
  await page.getByLabel('Message Parallax').waitFor({ timeout: 10000 });
  await page.getByText(/Reduced graphics mode/).first().waitFor({ timeout: 10000 });
  assert(await page.locator('canvas').count() === 0, 'WebGL preflight: reduced-graphics workspace should not mount canvases');
  assert(await page.evaluate(() => !document.createElement('canvas').getContext('webgl')), 'WebGL preflight: test browser unexpectedly created a WebGL context');
  assert(errors.length === 0, `WebGL preflight: browser errors: ${errors.join(' | ')}`);
  report.webglPreflight = { reducedGraphicsWorkspace: true, canvasCount: 0, browserErrors: 0 };
  await browser.close();
}

const normal = staticServer();
const fallback = staticServer({ failSkia: true });
const api = apiServer();
const report = {
  releaseSpecId: 'P2-V0.13.0',
  conversationPolicySpecId: 'P2-V0.5.0',
  viewports: [],
  liveResponseTreatment: null,
  buildPlan: null,
  fallback: null,
  webglPreflight: null,
};
let browser;

try {
  await Promise.all([listen(normal, 8765), listen(fallback, 8766), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  await inspectViewport(browser, 'mobile', 390, 844, report);
  await inspectViewport(browser, 'tablet', 768, 1024, report);
  await inspectViewport(browser, 'desktop', 1440, 900, report);
  await inspectFallback(browser, report);
  await inspectWebGlPreflight(report);
  writeFileSync(`${evidenceDir}/report.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser?.close();
  normal.close();
  fallback.close();
  api.close();
}
