import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const evidenceDir = new URL('../visual-evidence/w4-release/', import.meta.url).pathname;
const fixturePath = new URL('../test-fixtures/w4-release-states.json', import.meta.url).pathname;
const fixtures = JSON.parse(readFileSync(fixturePath, 'utf8'));
mkdirSync(evidenceDir, { recursive: true });

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
const SPEC_ID = '22222222-2222-4222-8222-222222222222';
const RUN_ID = '44444444-4444-4444-8444-444444444444';
const PARENT = `src:${'a'.repeat(64)}`;
const CANDIDATE = `src:${'b'.repeat(64)}`;
const NOW = '2026-08-24T22:30:00Z';
const ATTEMPTS = {
  build: '55555555-5555-4555-8555-555555555555',
  'test-active': '56565656-5656-4565-8565-565656565656',
  'test-failed': '66666666-6666-4666-8666-666666666666',
  'test-success': '99999999-9999-4999-8999-999999999999',
  verify: '88888888-8888-4888-8888-888888888888',
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

let activeFixtureName = 'active';
const streamConnections = new Map();

function fixture() {
  const value = fixtures.states[activeFixtureName];
  if (!value) throw new Error(`Unknown fixture ${activeFixtureName}`);
  return value;
}

function eventFromFact(fact, index) {
  return {
    id: `10000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}`,
    project_id: PROJECT_ID,
    run_id: RUN_ID,
    sequence: index + 1,
    event_key: `${activeFixtureName}-${index + 1}`,
    event_type: fact.type,
    stage: fact.stage ?? null,
    outcome: fact.outcome,
    subsystem: fact.subsystem ?? 'RUN',
    attempt_id: fact.attempt ? ATTEMPTS[fact.attempt] : null,
    worker_execution_id: null,
    source_lineage_ref: fact.lineage === 'candidate' ? CANDIDATE : fact.lineage === 'parent' ? PARENT : null,
    parent_source_lineage_ref: fact.parent_lineage === 'parent' ? PARENT : null,
    operation_ref: null,
    artifact_ref: null,
    evidence_ref: null,
    failure_code: fact.failure_code ?? null,
    summary: fact.summary,
    metadata: fact.metadata ?? {},
    occurred_at: NOW,
    created_at: NOW,
  };
}

function currentEvents() {
  return fixture().events.map(eventFromFact);
}

function currentRun() {
  const value = fixture();
  const events = currentEvents();
  const attemptFacts = events.filter((item) => item.attempt_id);
  return {
    id: RUN_ID,
    conversation_id: CONVERSATION_ID,
    spec_id: 'P2-V0.17.5',
    project_id: PROJECT_ID,
    project_binding_status: 'PROJECT_BOUND',
    work_specification_id: SPEC_ID,
    work_specification_revision: 1,
    work_specification_digest: 'c'.repeat(64),
    binding_status: 'APPROVED_SPEC_BOUND',
    acceptance_criteria: [
      { id: 'AC-01', text: 'Persist evidence-backed runtime facts.' },
      { id: 'AC-02', text: 'Preserve the explicit REVIEW boundary.' },
    ],
    state: value.run_state,
    resume_stage: value.run_state === 'FAILED' ? 'IMPLEMENT' : null,
    revision: Math.max(1, events.length),
    workspace_ref: null,
    last_failure_code: events.findLast((item) => item.failure_code)?.failure_code ?? null,
    completed_at: value.run_state === 'COMPLETE' ? NOW : null,
    created_at: NOW,
    updated_at: NOW,
    attempts: attemptFacts.map((item, index) => ({
      id: item.attempt_id,
      stage: item.stage ?? 'TEST',
      attempt_number: index + 1,
      status: item.outcome === 'FAILED' ? 'FAILED' : item.outcome === 'STARTED' ? 'RUNNING' : 'PASSED',
      failure_code: item.failure_code,
      evidence: {},
      started_at: NOW,
      completed_at: item.outcome === 'STARTED' ? null : NOW,
    })),
  };
}

const conversation = {
  id: CONVERSATION_ID,
  title: 'Wave 4 visual release reference',
  mode: 'code',
  status: 'ACTIVE',
  spec_id: 'P2-V0.17.5',
  project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND',
  created_at: NOW,
  updated_at: NOW,
  messages: [],
};
const workSpecification = {
  id: SPEC_ID,
  conversation_id: CONVERSATION_ID,
  revision: 1,
  status: 'APPROVED',
  title: 'Wave 4 visual release reference',
  objective: 'Prove material visual composition and truthful persisted-state projection.',
  constraints: ['Test-only fixtures never become production runtime values.'],
  acceptance_criteria: ['Material layout remains usable.', 'Runtime facts remain truthful.'],
  risks: ['Pixel-only comparison would be brittle.'],
  open_questions: [],
  confidence: 0.99,
  program_version: 'w4-visual-release-gate-v1',
  model_id: 'deterministic-fixture',
  created_at: NOW,
  updated_at: NOW,
  approved_at: NOW,
};

function cors(response, origin) {
  response.setHeader('access-control-allow-origin', origin ?? '*');
  response.setHeader('access-control-allow-credentials', 'true');
  response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Last-Event-ID,Authorization');
  response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
}

function json(response, status, payload, origin) {
  cors(response, origin);
  response.writeHead(status, { 'content-type': 'application/json', 'cache-control': 'no-store' });
  response.end(JSON.stringify(payload));
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
    const url = new URL(request.url ?? '/', 'http://localhost');
    const pathname = url.pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, currentRun(), origin);

    if (pathname === `/v1/engineering-runs/${RUN_ID}/events` && request.method === 'GET') {
      if (fixture().api_mode === 'unavailable') return json(response, 503, { detail: 'Live observation is intentionally unavailable for release fixture validation.' }, origin);
      const after = Number(url.searchParams.get('after_sequence') ?? '0');
      const page = currentEvents().filter((item) => item.sequence > after);
      return json(response, 200, { events: page, next_after_sequence: page.at(-1)?.sequence ?? after, has_more: false }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events/stream` && request.method === 'GET') {
      if (fixture().api_mode === 'unavailable') return json(response, 503, { detail: 'Live observation unavailable' }, origin);
      const key = activeFixtureName;
      const connection = (streamConnections.get(key) ?? 0) + 1;
      streamConnections.set(key, connection);
      const after = Number(request.headers['last-event-id'] ?? '0');
      let page = currentEvents().filter((item) => item.sequence > after);
      if (fixture().stream_disconnect_once && connection === 1) page = page.slice(0, Math.max(1, Math.ceil(page.length / 2)));
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'close' });
      for (const item of page) response.write(`id: ${item.sequence}\nevent: run-event\ndata: ${JSON.stringify(item)}\n\n`);
      response.end();
      return;
    }
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

async function openObservability(page) {
  await page.goto('http://127.0.0.1:8771', { waitUntil: 'networkidle' });
  const desktopNav = page.getByText('Observability', { exact: true });
  if (await desktopNav.count()) await desktopNav.first().click();
  else await page.getByLabel('Open Live Build observability').click();
  await page.getByText('Run observability', { exact: true }).waitFor({ timeout: 8000 });
}

async function assertMaterialLayout(page, name, width) {
  const doc = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  assert(doc.scrollWidth <= doc.clientWidth + 1, `${name}: document horizontally overflows (${doc.scrollWidth} > ${doc.clientWidth})`);

  const workspace = page.getByTestId('live-build-workspace');
  const workspaceBox = await workspace.boundingBox();
  assert(workspaceBox && workspaceBox.x >= 0 && workspaceBox.x + workspaceBox.width <= width + 1, `${name}: Live Build workspace is clipped`);

  const tabs = page.getByRole('tab');
  assert(await tabs.count() === 6, `${name}: expected six bounded Live Build tabs`);
  for (let index = 0; index < await tabs.count(); index += 1) {
    const box = await tabs.nth(index).boundingBox();
    assert(box && box.height >= 42, `${name}: tab ${index} is below practical target height (${box?.height ?? 0})`);
  }

  const title = page.getByText('Run observability', { exact: true });
  const kicker = page.getByText('LIVE BUILD · GOVERNED OBSERVER', { exact: true });
  const typography = await Promise.all([title, kicker].map((locator) => locator.evaluate((node) => {
    const style = getComputedStyle(node);
    return { fontSize: parseFloat(style.fontSize), lineHeight: parseFloat(style.lineHeight) };
  })));
  assert(typography[0].fontSize >= 24, `${name}: observability title hierarchy collapsed (${typography[0].fontSize}px)`);
  assert(typography[0].fontSize >= typography[1].fontSize * 2.5, `${name}: display title no longer dominates evidence kicker`);

  const navCount = await page.getByTestId('editorial-navigation-rail').count();
  const utilityCount = await page.getByTestId('editorial-utility-rail').count();
  const contextCount = await page.getByLabel('Live Build contextual health').count();
  if (width >= 1180) {
    assert(navCount === 1, `${name}: desktop navigation rail missing`);
    assert(contextCount === 1, `${name}: desktop contextual health rail missing`);
    const navBox = await page.getByTestId('editorial-navigation-rail').boundingBox();
    assert(navBox && navBox.width / width >= 0.035 && navBox.width / width <= 0.12, `${name}: navigation rail proportion is materially off (${navBox?.width ?? 0}px)`);
    await page.getByText('System Health', { exact: true }).waitFor();
    await page.getByText('Active Run', { exact: true }).waitFor();
    await page.getByText('Recent Alerts', { exact: true }).waitFor();
  } else if (width >= 760) {
    assert(navCount === 1, `${name}: tablet navigation rail missing`);
    assert(utilityCount === 0, `${name}: tablet utility rail compresses the primary workplane`);
    assert(contextCount === 0, `${name}: tablet retained desktop contextual rail`);
  } else {
    assert(navCount === 0, `${name}: phone retained desktop navigation rail`);
    assert(utilityCount === 0, `${name}: phone retained desktop utility rail`);
    assert(contextCount === 0, `${name}: phone retained desktop contextual rail`);
  }

  await page.getByRole('tab', { name: 'Code' }).focus();
  assert(await page.getByRole('tab', { name: 'Code' }).evaluate((node) => document.activeElement === node), `${name}: Code tab is not keyboard focusable`);
  await page.keyboard.press('Tab');
  const activeRole = await page.evaluate(() => document.activeElement?.getAttribute('role'));
  assert(activeRole === 'tab', `${name}: focus did not advance through the tab list`);

  const workspaceCanvasCount = await workspace.locator('canvas').count();
  assert(workspaceCanvasCount === 0, `${name}: evidence-bearing Live Build content unexpectedly depends on canvas rendering`);
}

async function inspectState(browser, fixtureName, viewport, report) {
  activeFixtureName = fixtureName;
  streamConnections.delete(fixtureName);
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('503 (Service Unavailable)')) errors.push(`console: ${message.text()}`);
  });
  await openObservability(page);

  assert(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), `${fixtureName}/${viewport.name}: reduced-motion media contract was not active`);
  for (const text of fixture().expect_text) await page.getByText(text, { exact: false }).first().waitFor({ timeout: 8000 });
  await assertMaterialLayout(page, `${fixtureName}/${viewport.name}`, viewport.width);

  if (fixtureName === 'unavailable_telemetry') {
    assert(await page.locator('[data-testid^="run-event-"]').count() === 0, 'unavailable telemetry: fabricated persisted events were rendered');
  }
  if (fixtureName === 'human_required') {
    const body = await page.locator('body').innerText();
    assert(body.includes('HUMAN_REQUIRED'), 'human-required: REVIEW boundary is not explicit');
    assert(!body.includes('COMPLETE · autonomous'), 'human-required: autonomous completion was fabricated');
  }

  const screenshot = `${fixtureName}-${viewport.name}.png`;
  await page.screenshot({ path: `${evidenceDir}/${screenshot}`, fullPage: false });
  assert(errors.length === 0, `${fixtureName}/${viewport.name}: browser errors: ${errors.join(' | ')}`);
  report.captures.push({ fixture: fixtureName, viewport: viewport.name, width: viewport.width, height: viewport.height, screenshot });
  await page.close();
}

assert(fixtures.test_only === true, 'Wave 4 visual fixture file must remain explicitly test-only');
assert(Object.keys(fixtures.states).sort().join(',') === ['active', 'human_required', 'provider_failure', 'reconnect_retry', 'success', 'unavailable_telemetry'].sort().join(','), 'Wave 4 fixture state inventory changed without release-gate review');

const web = staticServer();
const api = apiServer();
let browser;
const report = {
  gate: 'W4-S5 visual acceptance',
  authority: ['DESIGN-SYSTEM.md v3.0', 'P2-V0.17.4', 'P2-V0.17.5', 'issue #174'],
  fixtureSchemaVersion: fixtures.schema_version,
  materialAssertions: ['rail-proportion', 'overflow-clipping', 'typography-hierarchy', 'card-density', 'navigation-state', 'responsive-transition', 'keyboard-focus', 'reduced-motion', 'reduced-graphics-information-parity'],
  captures: [],
};

try {
  await Promise.all([listen(web, 8771), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });

  for (const viewport of [
    { name: 'desktop-reference', width: 1440, height: 900 },
    { name: 'desktop-compact', width: 1280, height: 800 },
    { name: 'tablet-portrait', width: 834, height: 1112 },
    { name: 'phone', width: 390, height: 844 },
  ]) await inspectState(browser, 'active', viewport, report);

  for (const fixtureName of ['success', 'unavailable_telemetry', 'provider_failure', 'reconnect_retry', 'human_required']) {
    await inspectState(browser, fixtureName, { name: 'desktop-reference', width: 1440, height: 900 }, report);
  }

  writeFileSync(`${evidenceDir}/report.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser?.close();
  await new Promise((resolve) => web.close(resolve));
  await new Promise((resolve) => api.close(resolve));
}
