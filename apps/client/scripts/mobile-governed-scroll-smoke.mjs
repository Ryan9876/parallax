import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const evidenceDir = new URL('../visual-evidence/', import.meta.url).pathname;
mkdirSync(evidenceDir, { recursive: true });

const mime = {
  '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.json': 'application/json',
  '.wasm': 'application/wasm', '.png': 'image/png', '.svg': 'image/svg+xml',
};
const PROJECT_ID = '10101010-1010-4010-8010-101010101010';
const CONVERSATION_ID = '20202020-2020-4020-8020-202020202020';
const SPEC_ID = '30303030-3030-4030-8030-303030303030';
const RUN_ID = '40404040-4040-4040-8040-404040404040';
const now = '2026-08-26T21:40:00Z';

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
  id: PROJECT_ID, slug: 'governed-logo-project', name: 'Governed Logo Project', description: null,
  repository_ref: 'github:owner/governed-logo-project', workspace_ref: `project:${PROJECT_ID}`, status: 'active', created_at: now, updated_at: now,
};
const conversation = {
  id: CONVERSATION_ID, title: 'Mobile governed build flow', mode: 'code', status: 'ACTIVE', spec_id: 'P2-V0.18.7',
  project_id: PROJECT_ID, project_binding_status: 'PROJECT_BOUND', created_at: now, updated_at: now,
  messages: [
    { id: 'mobile-scroll-user', role: 'user', content: 'Update the Parallax logo with a small governed visual change.', status: 'complete', created_at: now },
    { id: 'mobile-scroll-assistant', role: 'assistant', content: 'The approved work specification is bound to an active implementation run.', status: 'complete', created_at: now },
  ],
};
const workSpecification = {
  id: SPEC_ID, conversation_id: CONVERSATION_ID, revision: 1, status: 'APPROVED', title: 'Bounded logo update',
  objective: 'Apply one bounded logo motion adjustment without changing protected execution authority.',
  constraints: ['Keep the existing application shell.', 'Preserve protected execution and provider boundaries.'],
  acceptance_criteria: ['Keep the visual change bounded.', 'Preserve mobile usability.', 'Preserve protected authority.'],
  risks: ['Engineering detail must not dominate the phone workspace.'], open_questions: [], confidence: 0.99,
  program_version: 'mobile-governed-scroll-smoke', model_id: 'test-model', created_at: now, updated_at: now, approved_at: now,
};
const engineeringRun = {
  id: RUN_ID, conversation_id: CONVERSATION_ID, spec_id: 'P2-V0.18.7', project_id: PROJECT_ID, project_binding_status: 'PROJECT_BOUND',
  work_specification_id: SPEC_ID, work_specification_revision: 1, work_specification_digest: 'a'.repeat(64), binding_status: 'APPROVED_SPEC_BOUND',
  acceptance_criteria: workSpecification.acceptance_criteria.map((text, index) => ({ id: `AC-0${index + 1}`, text })),
  state: 'IMPLEMENT', resume_stage: null, revision: 2, workspace_ref: null, last_failure_code: null, completed_at: null,
  created_at: now, updated_at: now,
  attempts: [
    { id: 'a1', stage: 'SPECIFY', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
    { id: 'a2', stage: 'PLAN', attempt_number: 1, status: 'PASSED', failure_code: null, evidence: {}, started_at: now, completed_at: now },
    { id: 'a3', stage: 'IMPLEMENT', attempt_number: 1, status: 'RUNNING', failure_code: null, evidence: {}, started_at: now, completed_at: now },
  ],
};
function cors(response, origin) {
  response.setHeader('access-control-allow-origin', origin ?? '*');
  response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization');
  response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
}
function json(response, status, body, origin) { cors(response, origin); const encoded = Buffer.from(JSON.stringify(body)); response.writeHead(status, { 'content-type': 'application/json', 'content-length': encoded.length }); response.end(encoded); }
function apiServer() {
  return createServer((request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') { cors(response, origin); response.writeHead(204); response.end(); return; }
    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/projects' && request.method === 'GET') return json(response, 200, [project], origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${CONVERSATION_ID}/work-specifications/approved` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/engineering-runs/conversation/${CONVERSATION_ID}/latest` && request.method === 'GET') return json(response, 200, engineeringRun, origin);
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

const web = staticServer(); const api = apiServer(); let browser;
try {
  await Promise.all([listen(web, 8773), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  await page.goto('http://127.0.0.1:8773', { waitUntil: 'networkidle' });
  await page.getByTestId('mobile-guided-shell').waitFor({ timeout: 10000 });
  const nav = page.getByTestId('mobile-bottom-navigation');
  const navBefore = await nav.boundingBox();
  const composerBefore = await page.getByLabel('Message Parallax').boundingBox();
  assert(navBefore && composerBefore, 'mobile guided scroll: navigation/composer not measurable');

  await page.getByRole('tab', { name: 'Project' }).click();
  await page.getByTestId('mobile-project-workspace').waitFor({ timeout: 5000 });
  await page.getByText('Governed Logo Project', { exact: true }).waitFor();
  await page.getByText('Mobile governed build flow', { exact: true }).waitFor();
  assert(await page.getByLabel('Message Parallax').count() === 0, 'mobile guided scroll: composer must not compete with Project workspace');

  await page.getByRole('tab', { name: 'Chat' }).click();
  const composerAfterProject = await page.getByLabel('Message Parallax').boundingBox();
  assert(composerAfterProject && Math.abs(composerAfterProject.y - composerBefore.y) <= 2, 'mobile guided scroll: composer did not return after Project navigation');

  await page.getByRole('tab', { name: 'Build' }).click();
  const build = page.getByTestId('mobile-build-workspace');
  await build.waitFor({ timeout: 5000 });
  await page.getByText('Implementation', { exact: true }).waitFor();
  await page.getByText('Current', { exact: true }).waitFor();
  assert(await page.getByLabel('Message Parallax').count() === 0, 'mobile guided scroll: composer must not compete with Build workspace');

  const before = await build.evaluate((node) => ({ scrollTop: node.scrollTop, scrollHeight: node.scrollHeight, clientHeight: node.clientHeight }));
  assert(before.scrollHeight > before.clientHeight + 40, `mobile guided scroll: Build workspace should be vertically scrollable (${before.scrollHeight} <= ${before.clientHeight})`);
  await page.getByText('View full engineering evidence').scrollIntoViewIfNeeded();
  await page.waitForTimeout(100);
  const after = await build.evaluate((node) => ({ scrollTop: node.scrollTop, scrollHeight: node.scrollHeight, clientHeight: node.clientHeight }));
  const navAfter = await nav.boundingBox();
  assert(after.scrollTop > 0, 'mobile guided scroll: lower Build evidence was not reachable by scrolling');
  assert(navAfter && Math.abs(navAfter.y - navBefore.y) <= 2, 'mobile guided scroll: bottom navigation moved while Build content scrolled');

  await page.getByRole('tab', { name: 'Chat' }).click();
  const composerAfter = await page.getByLabel('Message Parallax').boundingBox();
  assert(composerAfter && Math.abs(composerAfter.y - composerBefore.y) <= 2, 'mobile guided scroll: composer did not return to its stable Chat position');
  assert(errors.length === 0, `mobile guided scroll: browser errors: ${errors.join(' | ')}`);
  await page.screenshot({ path: `${evidenceDir}/mobile-guided-build-scroll.png`, fullPage: true });
  console.log(JSON.stringify({ viewport: { width: 390, height: 844 }, before, after, navStable: true, projectDestination: true, composerStable: true, currentStage: 'Implementation' }, null, 2));
  await page.close();
} finally {
  await browser?.close(); web.close(); api.close();
}
