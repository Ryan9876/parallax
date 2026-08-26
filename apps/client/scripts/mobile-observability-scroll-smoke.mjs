import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const evidenceDir = new URL('../visual-evidence/', import.meta.url).pathname;
mkdirSync(evidenceDir, { recursive: true });
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png', '.svg': 'image/svg+xml' };
const PROJECT_ID = 'b33db91f-4445-4108-b5fc-877ef3d3e208';
const CONVERSATION_ID = '70707070-7070-4070-8070-707070707070';
const SPEC_ID = '80808080-8080-4080-8080-808080808080';
const RUN_ID = 'e65305f8-63f8-47e1-ac6c-2db0cd4dab7e';
const now = '2026-08-26T21:58:18.903014Z';
function assert(condition, message) { if (!condition) throw new Error(message); }
function listen(server, port) { return new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', () => resolve(server)); }); }
function staticServer() {
  return createServer((request, response) => {
    const rawPath = new URL(request.url ?? '/', 'http://localhost').pathname;
    const relative = rawPath === '/' ? 'index.html' : rawPath.replace(/^\/+/, '');
    const target = normalize(join(root, relative));
    if (!target.startsWith(normalize(root)) || !existsSync(target)) { response.writeHead(404); response.end('not found'); return; }
    response.writeHead(200, { 'content-type': mime[extname(target)] ?? 'application/octet-stream', 'cache-control': 'no-store' });
    createReadStream(target).pipe(response);
  });
}
const project = {
  id: PROJECT_ID, slug: 'parallax-logo-project', name: 'Parallax Logo Project', description: null,
  repository_ref: 'github:owner/parallax-logo-project', workspace_ref: `project:${PROJECT_ID}`, status: 'active', created_at: now, updated_at: now,
};
const conversation = {
  id: CONVERSATION_ID, title: 'Parallax logo motion', mode: 'code', status: 'ACTIVE', spec_id: 'P2-V0.18.7', project_id: PROJECT_ID,
  project_binding_status: 'PROJECT_BOUND', created_at: now, updated_at: now,
  messages: [{ id: 'm1', role: 'user', content: 'Update the Parallax logo.', status: 'complete', created_at: now }],
};
const workSpecification = {
  id: SPEC_ID, conversation_id: CONVERSATION_ID, revision: 1, status: 'APPROVED', title: 'Add slow continuous rotation to the Parallax logo',
  objective: 'Apply one bounded visual change.', constraints: ['Preserve protected execution boundaries.'],
  acceptance_criteria: ['Keep the change bounded.', 'Preserve mobile usability.'], risks: ['Engineering evidence must remain reachable without becoming primary navigation.'],
  open_questions: [], confidence: 0.99, program_version: 'mobile-observability-scroll-smoke', model_id: 'test-model', created_at: now, updated_at: now, approved_at: now,
};
const engineeringRun = {
  id: RUN_ID, conversation_id: CONVERSATION_ID, spec_id: 'P2-V0.18.7', project_id: PROJECT_ID, project_binding_status: 'PROJECT_BOUND',
  work_specification_id: SPEC_ID, work_specification_revision: 1, work_specification_digest: 'a'.repeat(64), binding_status: 'APPROVED_SPEC_BOUND',
  acceptance_criteria: workSpecification.acceptance_criteria.map((text, index) => ({ id: `AC-0${index + 1}`, text })), state: 'IMPLEMENT', resume_stage: null,
  revision: 2, workspace_ref: null, last_failure_code: null, completed_at: null, created_at: now, updated_at: now,
  attempts: [
    { id: 'a1', stage: 'SPECIFY', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
    { id: 'a2', stage: 'PLAN', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
  ],
};
const events = [
  { sequence: 1, event_type: 'RUN_CREATED', stage: 'SPECIFY', outcome: 'INFO', subsystem: 'RUN', summary: 'Engineering Run created with canonical Project and approved Work Specification binding.' },
  { sequence: 2, event_type: 'STAGE_RESULT', stage: 'SPECIFY', outcome: 'SUCCEEDED', subsystem: 'RUN', summary: 'Protected SPECIFY attempt recorded as PASSED.' },
  { sequence: 3, event_type: 'STAGE_RESULT', stage: 'PLAN', outcome: 'SUCCEEDED', subsystem: 'RUN', summary: 'Protected PLAN attempt recorded as PASSED.' },
].map((event) => ({ id: `90909090-9090-4090-8090-${String(event.sequence).padStart(12, '0')}`, project_id: PROJECT_ID, run_id: RUN_ID, event_key: `mobile-observer-${event.sequence}`, attempt_id: null, worker_execution_id: null, source_lineage_ref: null, parent_source_lineage_ref: null, operation_ref: null, artifact_ref: null, evidence_ref: null, failure_code: null, metadata: {}, occurred_at: now, created_at: now, ...event }));
function cors(response, origin) { response.setHeader('access-control-allow-origin', origin ?? '*'); response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Last-Event-ID,Authorization'); response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS'); }
function json(response, status, payload, origin) { cors(response, origin); response.writeHead(status, { 'content-type': 'application/json' }); response.end(JSON.stringify(payload)); }
function apiServer() {
  return createServer((request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') { cors(response, origin); response.writeHead(204); response.end(); return; }
    const url = new URL(request.url ?? '/', 'http://localhost'); const pathname = url.pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/projects' && request.method === 'GET') return json(response, 200, [project], origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, engineeringRun, origin);
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events` && request.method === 'GET') {
      const after = Number(url.searchParams.get('after_sequence') ?? '0'); const page = events.filter((event) => event.sequence > after);
      return json(response, 200, { events: page, next_after_sequence: page.at(-1)?.sequence ?? after, has_more: false }, origin);
    }
    if (pathname === `/v1/engineering-runs/${RUN_ID}/events/stream` && request.method === 'GET') {
      const after = Number(request.headers['last-event-id'] ?? '0'); const page = events.filter((event) => event.sequence > after);
      cors(response, origin); response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      for (const event of page) response.write(`id: ${event.sequence}\nevent: run-event\ndata: ${JSON.stringify(event)}\n\n`);
      response.end(); return;
    }
    return json(response, 404, { detail: 'not found' }, origin);
  });
}
const web = staticServer(); const api = apiServer(); let browser;
try {
  await Promise.all([listen(web, 8774), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  await page.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' });
  await page.getByTestId('mobile-guided-shell').waitFor({ timeout: 10000 });
  assert(await page.getByRole('tab', { name: 'Observability' }).count() === 0, 'mobile evidence: Observability must not be a primary mobile destination');
  await page.getByRole('tab', { name: 'Build' }).click();
  await page.getByTestId('mobile-build-workspace').waitFor({ timeout: 5000 });
  await page.getByLabel('Open build details', { exact: true }).click();
  await page.getByText('Run observability', { exact: true }).waitFor({ timeout: 10000 });
  await page.getByText('Sequence 3', { exact: true }).waitFor({ timeout: 10000 });

  const scroll = page.getByTestId('live-build-mobile-scroll');
  const support = page.getByTestId('observability-evidence-audit');
  await scroll.waitFor({ timeout: 5000 }); await support.waitFor({ state: 'attached', timeout: 5000 });
  const before = await scroll.evaluate((node) => ({ scrollTop: node.scrollTop, scrollHeight: node.scrollHeight, clientHeight: node.clientHeight, top: node.getBoundingClientRect().top, bottom: node.getBoundingClientRect().bottom }));
  assert(before.scrollHeight > before.clientHeight + 250, `mobile evidence: detail content is not meaningfully scrollable (${before.scrollHeight} <= ${before.clientHeight})`);
  await support.evaluate((node) => node.scrollIntoView({ block: 'center', behavior: 'instant' })); await page.waitForTimeout(120);
  const after = await scroll.evaluate((node) => ({ scrollTop: node.scrollTop, top: node.getBoundingClientRect().top, bottom: node.getBoundingClientRect().bottom }));
  const supportBox = await support.boundingBox();
  assert(after.scrollTop > 120, `mobile evidence: detail scroll did not advance (${after.scrollTop}px)`);
  assert(supportBox && supportBox.y < after.bottom && supportBox.y + supportBox.height > after.top, 'mobile evidence: lower evidence content is not reachable');
  assert(errors.length === 0, `mobile evidence: browser errors: ${errors.join(' | ')}`);
  await page.screenshot({ path: `${evidenceDir}/mobile-progressive-build-evidence.png`, fullPage: true });
  console.log(JSON.stringify({ viewport: { width: 390, height: 844 }, primaryDestinations: ['Chat', 'Build', 'Project'], observabilityPrimary: false, durableSequence: 3, before, after, progressiveDisclosure: true }, null, 2));
  await page.close();
} finally { await browser?.close(); await new Promise((resolve) => web.close(resolve)); await new Promise((resolve) => api.close(resolve)); }
