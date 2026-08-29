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

const PROJECT_ID = '77777777-7777-4777-8777-777777777777';
const OTHER_PROJECT_ID = '88888888-8888-4888-8888-888888888888';
const AMENDMENT_OBJECTIVE = 'Replace the approved objective entirely.';
const AMENDMENT_MESSAGE = 'Your request is different from the plan you approved. Parallax stopped before changing that approved work. Continue the approved work, or start a new goal for the new request.';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

function close(server) {
  return new Promise((resolve) => server.close(() => resolve()));
}

function staticServer({ failSkia = false } = {}) {
  return createServer((request, response) => {
    const rawPath = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (failSkia && rawPath === '/canvaskit.wasm') {
      response.writeHead(503, { 'content-type': 'text/plain' });
      response.end('CanvasKit intentionally unavailable for Code binding parity');
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

function project(id, name) {
  return {
    id,
    slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
    name,
    description: null,
    repository_ref: `github:owner/${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    workspace_ref: `project:${id}`,
    status: 'active',
    created_at: '2026-08-21T10:00:00Z',
    updated_at: '2026-08-21T10:00:00Z',
  };
}

function apiServer() {
  const projects = [project(OTHER_PROJECT_ID, 'Other Project'), project(PROJECT_ID, 'Code Binding Project')];
  let conversation = null;
  let specification = null;
  let engineeringRun = null;
  const codeConversationRequests = [];
  const autonomyRequests = [];

  function makeConversation(mode) {
    return {
      id: mode === 'code'
        ? `33333333-3333-4333-8333-${String(codeConversationRequests.length).padStart(12, '0')}`
        : '11111111-1111-4111-8111-111111111111',
      title: 'New conversation',
      mode,
      status: 'ACTIVE',
      spec_id: 'P2-V0.13.0',
      project_id: mode === 'code' ? PROJECT_ID : null,
      project_binding_status: mode === 'code' ? 'PROJECT_BOUND' : 'HISTORICAL_UNBOUND',
      created_at: '2026-08-21T10:00:00Z',
      updated_at: '2026-08-21T10:00:00Z',
      messages: [],
    };
  }

  function cors(response, origin) {
    response.setHeader('access-control-allow-origin', origin ?? '*');
    response.setHeader('access-control-allow-headers', 'Content-Type,Accept,Authorization');
    response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
  }

  function json(response, status, payload, origin) {
    cors(response, origin);
    response.writeHead(status, { 'content-type': 'application/json' });
    response.end(JSON.stringify(payload));
  }

  async function body(request) {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
  }

  const server = createServer(async (request, response) => {
    const origin = request.headers.origin;
    if (request.method === 'OPTIONS') {
      cors(response, origin);
      response.writeHead(204);
      response.end();
      return;
    }

    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname === '/v1/session' && request.method === 'GET') return json(response, 200, { authenticated: true }, origin);
    if (pathname === '/v1/projects' && request.method === 'GET') return json(response, 200, projects, origin);
    if (pathname === '/v1/conversations' && request.method === 'GET') return json(response, 200, conversation ? [conversation] : [], origin);

    if (pathname === '/v1/conversations' && request.method === 'POST') {
      const payload = await body(request);
      const mode = payload.mode === 'code' ? 'code' : 'reason';
      if (mode === 'code') {
        codeConversationRequests.push(payload);
        assert(payload.project_id === PROJECT_ID, 'Code conversation did not use the explicitly selected canonical Project ID');
        assert(!Object.hasOwn(payload, 'workspace_ref'), 'Code conversation request exposed workspace_ref');
      } else {
        assert(!Object.hasOwn(payload, 'project_id'), 'Reason conversation unexpectedly carried Project binding');
      }
      conversation = makeConversation(mode);
      specification = null;
      engineeringRun = null;
      return json(response, 200, conversation, origin);
    }

    if (/^\/v1\/conversations\/[^/]+$/.test(pathname) && request.method === 'GET') {
      return json(response, conversation ? 200 : 404, conversation ?? { detail: 'Conversation not found' }, origin);
    }
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/latest$/.test(pathname) && request.method === 'GET') {
      return json(response, 200, specification, origin);
    }
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/approved$/.test(pathname) && request.method === 'GET') {
      return json(response, 200, specification?.status === 'APPROVED' ? specification : null, origin);
    }
    if (/^\/v1\/engineering-runs\/conversation\/[^/]+\/latest$/.test(pathname) && request.method === 'GET') {
      return json(response, 200, engineeringRun, origin);
    }

    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/draft$/.test(pathname) && request.method === 'POST') {
      const now = new Date().toISOString();
      specification = {
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
      return json(response, 200, specification, origin);
    }

    if (/^\/v1\/work-specifications\/[^/]+\/approve$/.test(pathname) && request.method === 'POST') {
      const now = new Date().toISOString();
      specification = { ...specification, status: 'APPROVED', approved_at: now, updated_at: now };
      return json(response, 200, specification, origin);
    }

    if (pathname === '/v1/engineering-runs/activate' && request.method === 'POST') {
      const payload = await body(request);
      assert(specification?.status === 'APPROVED', 'Engineering Run activated without an approved build plan');
      assert(!Object.hasOwn(payload, 'project_id'), 'Engineering Run activation accepted caller Project identity');
      assert(!Object.hasOwn(payload, 'workspace_ref'), 'Engineering Run activation accepted caller workspace identity');
      const now = new Date().toISOString();
      engineeringRun = {
        id: '44444444-4444-4444-8444-444444444444',
        conversation_id: conversation.id,
        spec_id: conversation.spec_id,
        project_id: PROJECT_ID,
        project_binding_status: 'PROJECT_BOUND',
        work_specification_id: specification.id,
        work_specification_revision: specification.revision,
        work_specification_digest: 'a'.repeat(64),
        binding_status: 'APPROVED_SPEC_BOUND',
        acceptance_criteria: specification.acceptance_criteria.map((text, index) => ({ id: `AC-0${index + 1}`, text })),
        state: 'PLAN',
        resume_stage: null,
        revision: 1,
        workspace_ref: null,
        last_failure_code: null,
        completed_at: null,
        created_at: now,
        updated_at: now,
        attempts: [{
          id: '55555555-5555-4555-8555-555555555555',
          stage: 'SPECIFY',
          attempt_number: 1,
          status: 'PASSED',
          failure_code: null,
          evidence: { work_specification_id: specification.id },
          started_at: now,
          completed_at: now,
        }],
      };
      return json(response, 200, engineeringRun, origin);
    }

    if (/^\/v1\/engineering-runs\/[^/]+\/autonomous$/.test(pathname) && request.method === 'POST') {
      const payload = await body(request);
      autonomyRequests.push(payload);
      assert(payload.expected_revision === engineeringRun?.revision, 'autonomy request used a stale run revision');
      const now = new Date().toISOString();
      if (engineeringRun.state === 'PLAN') {
        engineeringRun = {
          ...engineeringRun,
          state: 'IMPLEMENT',
          revision: engineeringRun.revision + 1,
          updated_at: now,
          attempts: [...engineeringRun.attempts, {
            id: '66666666-6666-4666-8666-666666666666',
            stage: 'PLAN',
            attempt_number: 1,
            status: 'PASSED',
            failure_code: null,
            evidence: { executor_preflight: 'passed' },
            started_at: now,
            completed_at: now,
          }],
        };
      }
      return json(response, 200, {
        run: engineeringRun,
        stop_reason: 'IMPLEMENTATION_REQUIRED',
        steps: [{ stage: 'PLAN', outcome: 'PASSED', attempt_id: '66666666-6666-4666-8666-666666666666', replayed: false, tool_id: null }],
      }, origin);
    }

    if (/^\/v1\/conversations\/[^/]+\/responses$/.test(pathname) && request.method === 'POST') {
      const payload = await body(request);
      const now = new Date().toISOString();
      const user = { id: `user-${conversation.messages.length}`, role: 'user', content: String(payload.content ?? ''), status: 'complete', created_at: now };
      if (user.content === AMENDMENT_OBJECTIVE) {
        const assistant = { id: `assistant-amendment-${conversation.messages.length}`, role: 'assistant', content: AMENDMENT_MESSAGE, status: 'complete', created_at: now };
        conversation = { ...conversation, status: 'SPEC_AMENDMENT', messages: [...conversation.messages, user, assistant], updated_at: now };
        cors(response, origin);
        response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
        response.write(`event: state\ndata: ${JSON.stringify({ phase: 'THINKING' })}\n\n`);
        response.write(`event: state\ndata: ${JSON.stringify({ phase: 'SPEC_AMENDMENT' })}\n\n`);
        response.write(`event: amendment\ndata: ${JSON.stringify({ phase: 'SPEC_AMENDMENT', message_id: assistant.id, text: assistant.content, confidence: 0.96, scope_decision: 'SPEC_AMENDMENT' })}\n\n`);
        response.end();
        return;
      }

      const assistant = { id: `assistant-${conversation.messages.length}`, role: 'assistant', content: 'Your build goal is captured and ready for a build plan.', status: 'complete', created_at: now };
      conversation = { ...conversation, title: user.content.slice(0, 72), messages: [...conversation.messages, user, assistant], updated_at: now };
      cors(response, origin);
      response.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      response.write(`event: state\ndata: ${JSON.stringify({ phase: 'THINKING' })}\n\n`);
      response.write(`event: state\ndata: ${JSON.stringify({ phase: 'RESPONDING' })}\n\n`);
      response.write(`event: chunk\ndata: ${JSON.stringify({ text: assistant.content })}\n\n`);
      response.write(`event: complete\ndata: ${JSON.stringify({ phase: 'COMPLETE', message_id: assistant.id, confidence: 0.95, scope_decision: 'CONTINUE' })}\n\n`);
      response.end();
      return;
    }

    return json(response, 404, { detail: 'not found' }, origin);
  });

  return {
    server,
    codeConversationRequests,
    autonomyRequests,
    snapshot: () => ({ conversation, specification, engineeringRun }),
  };
}

const normal = staticServer();
const fallback = staticServer({ failSkia: true });
const apiInstance = apiServer();
let browser;

try {
  await Promise.all([listen(normal, 8770), listen(fallback, 8771), listen(apiInstance.server, 8010)]);
  browser = await chromium.launch({ headless: true });

  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://127.0.0.1:8770', { waitUntil: 'networkidle' });
  await page.getByLabel('Build').click();
  await page.getByText('Choose a project for Build').waitFor({ timeout: 5000 });
  await page.getByLabel('Select project Code Binding Project').click();
  await page.getByLabel('Message Parallax').fill('Implement the approved build goal.');
  await page.getByLabel('Send message').click();
  await page.getByText(/Your build goal is captured/).first().waitFor({ timeout: 10000 });
  await page.getByLabel('Create build plan').click();
  await page.getByText('Ready for your review').waitFor({ timeout: 5000 });
  await page.getByLabel('Approve build plan').click();
  await page.getByText('Plan approved').waitFor({ timeout: 5000 });
  await page.getByText('Making the changes').waitFor({ timeout: 10000 });
  await page.getByText('Following your approved plan').waitFor({ timeout: 5000 });
  await page.getByLabel('Continue work').waitFor({ timeout: 5000 });

  const bound = apiInstance.snapshot();
  assert(apiInstance.codeConversationRequests.length === 1, 'Code binding smoke created an unexpected number of Code conversations');
  assert(bound.specification?.status === 'APPROVED', 'approved build plan was not retained');
  assert(bound.engineeringRun?.project_id === PROJECT_ID, 'Engineering Run lost canonical Project binding');
  assert(bound.engineeringRun?.work_specification_id === bound.specification?.id, 'Engineering Run lost approved build-plan binding');
  assert(bound.engineeringRun?.state === 'IMPLEMENT', 'protected PLAN handoff did not advance to implementation boundary');
  assert(apiInstance.autonomyRequests.length >= 1, 'approved PLAN run never entered bounded autonomy');
  assert(await page.locator('canvas').count() > 0, 'Code binding smoke: Skia did not initialize');

  const reduced = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await reduced.goto('http://127.0.0.1:8771', { waitUntil: 'networkidle' });
  await reduced.getByText(/Reduced graphics mode/).first().waitFor({ timeout: 10000 });
  await reduced.getByText('Making the changes').waitFor({ timeout: 5000 });
  await reduced.getByText('Following your approved plan').waitFor({ timeout: 5000 });
  await reduced.getByLabel('Continue work').waitFor({ timeout: 5000 });
  assert(await reduced.locator('canvas').count() === 0, 'Reduced graphics Code binding should not require Skia canvases');
  await reduced.close();

  const priorConversationId = apiInstance.snapshot().conversation?.id;
  await page.getByLabel('Message Parallax').fill(AMENDMENT_OBJECTIVE);
  await page.getByLabel('Send message').click();
  await page.getByText('Your request changed').waitFor({ timeout: 10000 });
  await page.getByLabel('Start a new goal').waitFor({ timeout: 5000 });
  assert(await page.getByLabel('Message Parallax').getAttribute('placeholder') === 'Continue this goal…', 'desktop amendment composer guidance changed unexpectedly');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByTestId('mobile-guided-shell').waitFor({ state: 'visible', timeout: 5000 });
  await page.getByTestId('mobile-spec-amendment').waitFor({ state: 'visible', timeout: 5000 });
  const newGoal = page.getByLabel('Start as a new goal');
  await newGoal.waitFor({ state: 'visible', timeout: 5000 });
  const newGoalBox = await newGoal.boundingBox();
  assert(newGoalBox && newGoalBox.x >= 0 && newGoalBox.x + newGoalBox.width <= 391, 'mobile new-goal action is horizontally clipped');
  assert(newGoalBox.y >= 0 && newGoalBox.y < 844, 'mobile new-goal action is not viewport-reachable');
  await newGoal.click();
  await page.getByTestId('mobile-spec-amendment').waitFor({ state: 'detached', timeout: 5000 });
  assert(await page.getByLabel('Message Parallax').getAttribute('placeholder') === 'Describe the outcome you want…', 'fresh objective did not restore new-objective composer guidance');

  const fresh = apiInstance.snapshot();
  assert(fresh.conversation?.id !== priorConversationId, 'Start as a new goal did not create a fresh conversation');
  assert(fresh.conversation?.mode === 'code', 'fresh objective did not preserve Build mode');
  assert(fresh.conversation?.project_id === PROJECT_ID, 'fresh objective did not retain canonical Project binding');
  assert(fresh.specification === null, 'fresh objective inherited the prior build plan');
  assert(fresh.engineeringRun === null, 'fresh objective inherited the prior Engineering Run');
  assert(apiInstance.codeConversationRequests.length === 2, 'fresh objective did not create exactly one additional Code conversation');

  console.log(JSON.stringify({
    canonicalProjectBinding: true,
    approvedBuildPlanBinding: true,
    boundedAutonomyImplementContinuation: true,
    reducedGraphicsParity: true,
    desktopScopeBoundaryVisible: true,
    mobilePlainLanguageRecovery: true,
    freshObjectivePreservesCanonicalProject: true,
    freshObjectiveDoesNotInheritSpecOrRun: true,
  }, null, 2));
  await page.close();
} finally {
  await browser?.close();
  await Promise.all([close(normal), close(fallback), close(apiInstance.server)]);
}
