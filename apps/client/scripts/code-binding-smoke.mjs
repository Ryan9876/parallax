import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { createReadStream, existsSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
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

function staticServer({ failSkia = false } = {}) {
  return createServer((request, response) => {
    const rawPath = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (failSkia && rawPath === '/canvaskit.wasm') {
      response.writeHead(503, { 'content-type': 'text/plain' });
      response.end('CanvasKit intentionally unavailable for v0.8 Code binding parity');
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

function apiServer() {
  let conversation = null;
  let workSpecification = null;
  let engineeringRun = null;

  function makeConversation(mode) {
    return {
      id: mode === 'code' ? '33333333-3333-4333-8333-333333333333' : '11111111-1111-4111-8111-111111111111',
      title: 'New conversation',
      mode,
      status: 'ACTIVE',
      spec_id: 'P2-V0.8.0',
      created_at: '2026-08-21T10:00:00Z',
      updated_at: '2026-08-21T10:00:00Z',
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
    response.writeHead(status, { 'content-type': 'application/json' });
    response.end(JSON.stringify(body));
  }

  async function body(request) {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
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
      const payload = await body(request);
      conversation = makeConversation(payload.mode === 'code' ? 'code' : 'reason');
      workSpecification = null;
      engineeringRun = null;
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
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/approved$/.test(pathname) && request.method === 'GET') {
      json(response, 200, workSpecification?.status === 'APPROVED' ? workSpecification : null, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/draft$/.test(pathname) && request.method === 'POST') {
      const now = new Date().toISOString();
      workSpecification = {
        id: '22222222-2222-4222-8222-222222222222',
        conversation_id: conversation.id,
        revision: 1,
        status: 'DRAFT',
        title: 'Bound Code objective',
        objective: 'Implement the approved Code objective against an immutable Work Specification binding.',
        constraints: ['Preserve protected execution boundaries.'],
        acceptance_criteria: ['Code run binds to the approved revision.', 'Acceptance evidence remains server-owned.'],
        risks: ['A run could otherwise be silently retargeted.'],
        open_questions: [],
        confidence: 0.96,
        program_version: 'work-spec-v0.7.0',
        model_id: 'visual-smoke-model',
        created_at: now,
        updated_at: now,
        approved_at: null,
      };
      json(response, 200, workSpecification, origin);
      return;
    }
    if (/^\/v1\/work-specifications\/[^/]+\/approve$/.test(pathname) && request.method === 'POST') {
      const now = new Date().toISOString();
      workSpecification = { ...workSpecification, status: 'APPROVED', approved_at: now, updated_at: now };
      json(response, 200, workSpecification, origin);
      return;
    }
    if (/^\/v1\/engineering-runs\/conversation\/[^/]+\/latest$/.test(pathname) && request.method === 'GET') {
      json(response, 200, engineeringRun, origin);
      return;
    }
    if (pathname === '/v1/engineering-runs/activate' && request.method === 'POST') {
      const payload = await body(request);
      if (conversation?.mode !== 'code' || workSpecification?.status !== 'APPROVED') {
        json(response, 422, { detail: 'operator-approved work specification required before Code execution' }, origin);
        return;
      }
      if (!engineeringRun) {
        const now = new Date().toISOString();
        engineeringRun = {
          id: '44444444-4444-4444-8444-444444444444',
          conversation_id: conversation.id,
          spec_id: conversation.spec_id,
          work_specification_id: workSpecification.id,
          work_specification_revision: workSpecification.revision,
          work_specification_digest: 'a'.repeat(64),
          binding_status: 'APPROVED_SPEC_BOUND',
          acceptance_criteria: [
            { id: 'AC-01', text: workSpecification.acceptance_criteria[0] },
            { id: 'AC-02', text: workSpecification.acceptance_criteria[1] },
          ],
          state: 'PLAN',
          resume_stage: null,
          revision: 1,
          workspace_ref: null,
          last_failure_code: null,
          created_at: now,
          updated_at: now,
          completed_at: null,
          attempts: [{
            id: '55555555-5555-4555-8555-555555555555',
            stage: 'SPECIFY',
            attempt_number: 1,
            status: 'PASSED',
            failure_code: null,
            evidence: { work_specification_id: workSpecification.id },
            started_at: now,
            completed_at: now,
          }],
        };
      }
      assert(!payload.work_specification_id || payload.work_specification_id === workSpecification.id, 'activation used the wrong work specification');
      json(response, 200, engineeringRun, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/responses$/.test(pathname) && request.method === 'POST') {
      const payload = await body(request);
      const now = new Date().toISOString();
      const user = { id: 'user-code', role: 'user', content: String(payload.content ?? ''), status: 'complete', created_at: now };
      const assistant = { id: 'assistant-code', role: 'assistant', content: 'The Code objective is captured and ready for an explicit Work Specification.', status: 'complete', created_at: now };
      conversation.title = user.content.slice(0, 72);
      conversation.messages = [...conversation.messages, user, assistant];
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      response.write(`event: state\ndata: ${JSON.stringify({ phase: 'THINKING' })}\n\n`);
      response.write(`event: state\ndata: ${JSON.stringify({ phase: 'RESPONDING' })}\n\n`);
      response.write(`event: chunk\ndata: ${JSON.stringify({ text: assistant.content })}\n\n`);
      response.write(`event: state\ndata: ${JSON.stringify({ phase: 'VERIFYING' })}\n\n`);
      response.write(`event: complete\ndata: ${JSON.stringify({ phase: 'COMPLETE', message_id: assistant.id, confidence: 0.95, scope_decision: 'CONTINUE' })}\n\n`);
      response.end();
      return;
    }
    json(response, 404, { detail: 'not found' }, origin);
  });
}

async function exerciseCodeBinding(page) {
  await page.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await page.getByText('code', { exact: true }).click();
  await page.getByLabel('Message Parallax').fill('Implement the approved Code objective.');
  await page.getByLabel('Send message').click();
  await page.getByText(/The Code objective is captured/).waitFor({ timeout: 10000 });
  await page.getByLabel('Capture work specification').click();
  await page.getByText('SPEC · DRAFT').waitFor({ timeout: 5000 });
  await page.getByLabel('Approve work specification').click();
  await page.getByText('SPEC · APPROVED').waitFor({ timeout: 5000 });
  await page.getByText('Code run · PLAN').waitFor({ timeout: 5000 });
  await page.getByText(/BOUND · WORK SPEC R1 · 2 ACCEPTANCE CRITERIA/).waitFor({ timeout: 5000 });
}

const normal = staticServer();
const fallback = staticServer({ failSkia: true });
const api = apiServer();
let browser;

try {
  await Promise.all([listen(normal, 8770), listen(fallback, 8771), listen(api, 8010)]);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await exerciseCodeBinding(page);
  assert(await page.locator('canvas').count() > 0, 'Code binding smoke: Skia did not initialize');
  await page.close();

  const reduced = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await reduced.goto('http://127.0.0.1:8771', { waitUntil: 'networkidle' });
  await reduced.getByText(/Reduced graphics mode/).first().waitFor({ timeout: 10000 });
  await reduced.getByText('Code run · PLAN').waitFor({ timeout: 5000 });
  await reduced.getByText(/BOUND · WORK SPEC R1 · 2 ACCEPTANCE CRITERIA/).waitFor({ timeout: 5000 });
  assert(await reduced.locator('canvas').count() === 0, 'Reduced graphics Code binding should not require Skia canvases');
  await reduced.close();

  console.log(JSON.stringify({ codeSpecBinding: true, reducedGraphicsParity: true }, null, 2));
} finally {
  await browser?.close();
  normal.close();
  fallback.close();
  api.close();
}
