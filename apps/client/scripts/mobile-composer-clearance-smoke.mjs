import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const evidenceDir = new URL('../visual-evidence/', import.meta.url).pathname;
mkdirSync(evidenceDir, { recursive: true });
const mime = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png', '.svg': 'image/svg+xml' };
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

const conversation = {
  id: '77777777-7777-4777-8777-777777777777', title: 'Simple About Page', mode: 'code', status: 'ACTIVE', spec_id: 'P2-V0.18.7',
  project_id: '99999999-9999-4999-8999-999999999999', project_binding_status: 'PROJECT_BOUND',
  created_at: '2026-08-26T14:00:00Z', updated_at: '2026-08-26T14:00:00Z',
  messages: [
    { id: 'clearance-user', role: 'user', content: 'Add a simple About page to this application.', status: 'complete', created_at: '2026-08-26T14:00:00Z' },
    { id: 'clearance-assistant', role: 'assistant', content: 'The build objective is captured and ready for specification review.', status: 'complete', created_at: '2026-08-26T14:00:05Z' },
  ],
};
const workSpecification = {
  id: '88888888-8888-4888-8888-888888888888', conversation_id: conversation.id, revision: 4, status: 'DRAFT', title: 'Simple About Page',
  objective: 'Add a simple, accessible About page to the application.', constraints: ['Preserve current application behavior outside the About page change.'],
  acceptance_criteria: ['Use existing layout and styling.', 'Remain keyboard accessible.', 'Render without console errors.'],
  risks: ['The conversation live edge must remain visible while governed context changes.'], open_questions: [], confidence: 0.94,
  program_version: 'live-edge-continuity-smoke', model_id: 'test-model', created_at: '2026-08-26T14:00:10Z', updated_at: '2026-08-26T14:00:10Z', approved_at: null,
};
function apiServer() {
  function cors(response, origin) { response.setHeader('access-control-allow-origin', origin ?? '*'); response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization'); response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS'); }
  function json(response, status, body, origin) { cors(response, origin); const encoded = Buffer.from(JSON.stringify(body)); response.writeHead(status, { 'content-type': 'application/json', 'content-length': encoded.length }); response.end(encoded); }
  return createServer((request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') { cors(response, origin); response.writeHead(204); response.end(); return; }
    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, [conversation], origin);
    if (pathname === `/v1/conversations/${conversation.id}` && request.method === 'GET') return json(response, 200, conversation, origin);
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/latest` && request.method === 'GET') return json(response, 200, workSpecification, origin);
    if (pathname === `/v1/conversations/${conversation.id}/work-specifications/approved` && request.method === 'GET') return json(response, 200, null, origin);
    if (pathname === `/v1/engineering-runs/conversation/${conversation.id}/latest` && request.method === 'GET') return json(response, 200, null, origin);
    return json(response, 404, { detail: 'not found' }, origin);
  });
}

function threadGeometry(node) {
  let current = node.parentElement;
  while (current) {
    const style = getComputedStyle(current);
    if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
      return { scrollTop: current.scrollTop, scrollHeight: current.scrollHeight, clientHeight: current.clientHeight, distanceFromEnd: Math.max(0, current.scrollHeight - current.clientHeight - current.scrollTop) };
    }
    current = current.parentElement;
  }
  return null;
}

const staticSite = staticServer(); const api = apiServer(); let browser;
try {
  await Promise.all([listen(staticSite, 8767), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  await page.goto('http://127.0.0.1:8767', { waitUntil: 'networkidle' });
  await page.getByTestId('mobile-guided-shell').waitFor({ timeout: 10000 });
  await page.getByLabel('Review specification').waitFor({ timeout: 5000 });
  const response = page.getByLabel('Parallax response').last();
  await response.waitFor({ timeout: 5000 });

  const geometry = await response.evaluate(threadGeometry);
  const responseBox = await response.boundingBox();
  const inputBox = await page.getByLabel('Message Parallax').boundingBox();
  const navBox = await page.getByTestId('mobile-bottom-navigation').boundingBox();
  assert(responseBox && inputBox && navBox && geometry, 'mobile Chat continuity: required geometry was not measurable');
  assert(inputBox.y + inputBox.height <= navBox.y + 1, 'mobile Chat continuity: composer overlaps bottom navigation');
  assert(responseBox.y + responseBox.height <= inputBox.y - 6, `mobile Chat continuity: newest response intersects composer (${responseBox.y + responseBox.height} > ${inputBox.y - 6})`);
  assert(await page.getByLabel('Work specification').count() === 0, 'mobile Chat continuity: legacy inline Work Specification returned');
  assert(errors.length === 0, `mobile Chat continuity: browser errors: ${errors.join(' | ')}`);
  await page.screenshot({ path: `${evidenceDir}/mobile-composer-clearance.png` });

  await response.evaluate((node) => {
    let thread = node.parentElement;
    while (thread) { const style = getComputedStyle(thread); if (style.overflowY === 'auto' || style.overflowY === 'scroll') break; thread = thread.parentElement; }
    if (!thread) throw new Error('conversation scroll container not found');
    thread.scrollTop = thread.scrollHeight;
    const extra = document.createElement('div'); extra.dataset.liveEdgeFixture = 'follow';
    extra.textContent = Array.from({ length: 80 }, (_, index) => `Settled state update line ${index + 1}.`).join(' '); node.appendChild(extra);
  });
  await page.waitForTimeout(220);
  const afterSettledMutation = await response.evaluate(threadGeometry);
  assert(afterSettledMutation && afterSettledMutation.distanceFromEnd <= 4, `mobile Chat continuity: settled state mutation was not followed (${afterSettledMutation?.distanceFromEnd}px from end)`);
  assert(afterSettledMutation.scrollHeight - afterSettledMutation.clientHeight >= 180, 'mobile Chat continuity: scroll-away fixture did not create enough scrollable content');

  await response.evaluate((node) => {
    let thread = node.parentElement;
    while (thread) { const style = getComputedStyle(thread); if (style.overflowY === 'auto' || style.overflowY === 'scroll') break; thread = thread.parentElement; }
    if (!thread) throw new Error('conversation scroll container not found');
    thread.scrollTop = Math.max(0, thread.scrollHeight - thread.clientHeight - 180); thread.dispatchEvent(new Event('scroll'));
  });
  await page.waitForTimeout(80);
  await response.evaluate((node) => { const extra = document.createElement('div'); extra.dataset.liveEdgeFixture = 'preserve-scroll-away'; extra.textContent = Array.from({ length: 8 }, (_, index) => `Later state update ${index + 1}.`).join(' '); node.appendChild(extra); });
  await page.waitForTimeout(220);
  const afterScrollAwayMutation = await response.evaluate(threadGeometry);
  assert(afterScrollAwayMutation && afterScrollAwayMutation.distanceFromEnd >= 100, `mobile Chat continuity: deliberate scroll-away was overridden (${afterScrollAwayMutation?.distanceFromEnd}px from end)`);

  console.log(JSON.stringify({ viewport: { width: 390, height: 844 }, responseBox, inputBox, navBox, thread: geometry, responseClearance: inputBox.y - (responseBox.y + responseBox.height), settledMutationDistanceFromEnd: afterSettledMutation.distanceFromEnd, preservedScrollAwayDistanceFromEnd: afterScrollAwayMutation.distanceFromEnd, liveEdgePreserved: true, operatorScrollAwayPreserved: true, inlineSpecRemoved: true }, null, 2));
  await page.close();
} finally { await browser?.close(); staticSite.close(); api.close(); }