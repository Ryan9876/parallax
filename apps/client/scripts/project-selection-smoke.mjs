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

const ALPHA_ID = '11111111-1111-4111-8111-111111111111';
const BETA_ID = '22222222-2222-4222-8222-222222222222';
const CREATED_ID = '33333333-3333-4333-8333-333333333333';

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
  return new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
    server.closeAllConnections?.();
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

function project(id, name, repositoryRef = null) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return {
    id,
    slug,
    name,
    description: null,
    repository_ref: repositoryRef,
    workspace_ref: `project:${id}`,
    status: 'active',
    created_at: '2026-08-23T00:00:00Z',
    updated_at: '2026-08-23T00:00:00Z',
  };
}

function conversation(id, mode = 'reason', projectId = null, bindingStatus = 'HISTORICAL_UNBOUND') {
  return {
    id,
    title: mode === 'code' ? 'Code conversation' : 'Reason conversation',
    mode,
    status: 'ACTIVE',
    spec_id: 'P2-V0.15.8',
    project_id: projectId,
    project_binding_status: bindingStatus,
    created_at: '2026-08-23T00:00:00Z',
    updated_at: '2026-08-23T00:00:00Z',
    messages: [],
  };
}

function apiServer({ projects = [], initialConversation = null, rejectCode = false } = {}) {
  const state = {
    projects: [...projects],
    conversation: initialConversation,
    conversationPosts: [],
    projectPosts: [],
    projectGets: 0,
  };

  function cors(response, origin) {
    response.setHeader('access-control-allow-origin', origin ?? '*');
    response.setHeader('access-control-allow-headers', 'Content-Type,Accept');
    response.setHeader('access-control-allow-methods', 'GET,POST,OPTIONS');
  }

  function sendJson(response, status, payload, origin) {
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

    if (pathname === '/v1/projects' && request.method === 'GET') {
      state.projectGets += 1;
      sendJson(response, 200, state.projects, origin);
      return;
    }
    if (pathname === '/v1/projects' && request.method === 'POST') {
      const payload = await body(request);
      state.projectPosts.push(payload);
      const created = project(CREATED_ID, String(payload.name ?? ''), payload.repository_ref ?? null);
      state.projects = [created, ...state.projects];
      sendJson(response, 201, created, origin);
      return;
    }
    if (pathname === '/v1/conversations' && request.method === 'GET') {
      sendJson(response, 200, state.conversation ? [state.conversation] : [], origin);
      return;
    }
    if (pathname === '/v1/conversations' && request.method === 'POST') {
      const payload = await body(request);
      state.conversationPosts.push(payload);
      const mode = payload.mode === 'code' ? 'code' : 'reason';
      if (mode === 'code') {
        assert(typeof payload.project_id === 'string' && payload.project_id.length === 36, 'Code request omitted canonical project_id');
        assert(!Object.hasOwn(payload, 'workspace_ref'), 'Code request exposed workspace_ref');
        const selected = state.projects.find((candidate) => candidate.id === payload.project_id);
        if (rejectCode || !selected) {
          sendJson(response, 404, { detail: 'Project not found' }, origin);
          return;
        }
        state.conversation = conversation(
          '55555555-5555-4555-8555-555555555555',
          'code',
          selected.id,
          'PROJECT_BOUND',
        );
      } else {
        assert(!Object.hasOwn(payload, 'project_id'), 'Reason request unexpectedly carried project_id');
        assert(!Object.hasOwn(payload, 'workspace_ref'), 'Reason request unexpectedly carried workspace_ref');
        state.conversation = conversation('44444444-4444-4444-8444-444444444444', 'reason');
      }
      sendJson(response, 200, state.conversation, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+$/.test(pathname) && request.method === 'GET') {
      sendJson(response, state.conversation ? 200 : 404, state.conversation ?? { detail: 'Conversation not found' }, origin);
      return;
    }
    if (/^\/v1\/conversations\/[^/]+\/work-specifications\/(latest|approved)$/.test(pathname) && request.method === 'GET') {
      sendJson(response, 200, null, origin);
      return;
    }
    if (/^\/v1\/engineering-runs\/conversation\/[^/]+\/latest$/.test(pathname) && request.method === 'GET') {
      sendJson(response, 200, null, origin);
      return;
    }

    sendJson(response, 404, { detail: 'not found' }, origin);
  });

  return { server, state };
}

async function withApi(config, fn) {
  const instance = apiServer(config);
  await listen(instance.server, 8010);
  try {
    await fn(instance.state);
  } finally {
    await close(instance.server);
  }
}

async function withPage(viewport, fn) {
  const page = await browser.newPage({ viewport });
  try {
    await fn(page);
  } finally {
    await page.close().catch(() => undefined);
  }
}

async function scenario(name, fn) {
  console.log(`[project-selection] START ${name}`);
  await fn();
  console.log(`[project-selection] PASS ${name}`);
}

async function assertComposerVisible(page) {
  const box = await page.getByLabel('Message Parallax').boundingBox();
  assert(box, 'mobile Project flow lost the composer');
  assert(box.y + box.height <= 844, 'mobile Project flow pushed the composer outside the 390x844 viewport');
  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert(horizontalOverflow <= 1, `mobile Project flow introduced horizontal overflow (${horizontalOverflow}px)`);
}

const staticApp = staticServer();
let browser;

try {
  await listen(staticApp, 8774);
  browser = await chromium.launch({ headless: true });

  await scenario('desktop existing Project selection', async () => {
    await withApi({ projects: [project(ALPHA_ID, 'Alpha'), project(BETA_ID, 'Beta', 'github:owner/beta')] }, async (state) => {
      await withPage({ width: 1440, height: 900 }, async (page) => {
        await page.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' });

        assert(state.conversationPosts.length === 1, 'workspace startup should create one Reason conversation when history is empty');
        assert(JSON.stringify(state.conversationPosts[0]) === JSON.stringify({ mode: 'reason' }), 'Reason startup payload changed or acquired Project binding');
        assert(state.projectGets === 0, 'Project API should remain lazy during ordinary Reason startup');

        await page.getByText('code', { exact: true }).click();
        await page.getByText('Choose a Project for Code').waitFor({ timeout: 5000 });
        await page.getByLabel('Select Project Beta').click();
        await page.getByText('PROJECT · Beta').waitFor({ timeout: 5000 });

        const codePosts = state.conversationPosts.filter((payload) => payload.mode === 'code');
        assert(codePosts.length === 1, 'Project selection should create exactly one Code conversation');
        assert(codePosts[0].project_id === BETA_ID, 'Code creation did not use the explicitly selected canonical Project ID');
        assert(!Object.hasOwn(codePosts[0], 'workspace_ref'), 'workspace_ref leaked into Code conversation creation');
      });
    });
  });

  await scenario('mobile bound Project identity resolves on open', async () => {
    await withApi({
      projects: [project(ALPHA_ID, 'Alpha Mobile', 'github:owner/alpha-mobile')],
      initialConversation: conversation('12121212-1212-4212-8212-121212121212', 'code', ALPHA_ID, 'PROJECT_BOUND'),
    }, async (state) => {
      await withPage({ width: 390, height: 844 }, async (page) => {
        await page.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' });
        await page.getByTestId('mobile-workspace-header').getByText('Alpha Mobile', { exact: true }).waitFor({ timeout: 5000 });
        assert(state.projectGets === 1, 'mobile bound conversation did not resolve the canonical Project display name exactly once');
        assert(state.conversationPosts.length === 0, 'opening a bound mobile Build conversation should not create or rebind a conversation');

        await page.getByRole('tab', { name: 'Project' }).click();
        const workspace = page.getByTestId('mobile-project-workspace');
        await workspace.getByText('Alpha Mobile', { exact: true }).waitFor({ timeout: 5000 });
        await workspace.getByText('CURRENT PROJECT', { exact: true }).waitFor();
        await page.getByLabel('Change project').waitFor();
      });
    });
  });

  await scenario('mobile Project creation', async () => {
    await withApi({ projects: [] }, async (state) => {
      await withPage({ width: 390, height: 844 }, async (page) => {
        await page.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' });
        await page.getByLabel('Build').click();
        await page.getByText('Choose a project for Build').waitFor({ timeout: 5000 });
        await page.getByLabel('Project name').fill('Mobile Builder');
        await page.getByLabel('Repository identity').fill('owner/mobile-builder');
        await page.getByLabel('Create Project').click();
        await page.getByTestId('mobile-workspace-header').getByText('Mobile Builder', { exact: true }).waitFor({ timeout: 5000 });

        assert(state.projectPosts.length === 1, 'mobile create flow did not call Project creation exactly once');
        assert(state.projectPosts[0].name === 'Mobile Builder', 'Project create changed the requested name');
        assert(state.projectPosts[0].repository_ref === 'github:owner/mobile-builder', 'Project create did not normalize GitHub owner/repository shorthand to canonical repository identity');
        const codePosts = state.conversationPosts.filter((payload) => payload.mode === 'code');
        assert(codePosts.length === 1 && codePosts[0].project_id === CREATED_ID, 'mobile Code creation did not bind the server-returned canonical Project ID');
        await assertComposerVisible(page);

        await page.getByRole('tab', { name: 'Project' }).click();
        const workspace = page.getByTestId('mobile-project-workspace');
        await workspace.getByText('Mobile Builder', { exact: true }).waitFor({ timeout: 5000 });
        await page.getByLabel('Change project').waitFor();
      });
    });
  });

  await scenario('stale Project fails closed', async () => {
    await withApi({ projects: [project(ALPHA_ID, 'Stale Alpha')], rejectCode: true }, async (state) => {
      await withPage({ width: 1440, height: 900 }, async (page) => {
        await page.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' });
        await page.getByText('code', { exact: true }).click();
        await page.getByText('Project not found').waitFor({ timeout: 5000 });

        const codePosts = state.conversationPosts.filter((payload) => payload.mode === 'code');
        assert(codePosts.length === 1, 'stale Project failure retried Code creation instead of failing closed');
        assert(codePosts[0].project_id === ALPHA_ID, 'stale failure test did not first use the canonical owner-scoped Project');
        assert(state.conversationPosts.every((payload) => payload.mode !== 'code' || typeof payload.project_id === 'string'), 'failure path attempted unbound Code creation');
      });
    });
  });

  await scenario('historical unbound remains explicit', async () => {
    await withApi({
      projects: [project(ALPHA_ID, 'Unrelated Future Project')],
      initialConversation: conversation('66666666-6666-4666-8666-666666666666', 'code', null, 'HISTORICAL_UNBOUND'),
    }, async (state) => {
      await withPage({ width: 1440, height: 900 }, async (page) => {
        await page.goto('http://127.0.0.1:8774', { waitUntil: 'networkidle' });
        await page.getByText('HISTORICAL CODE · UNBOUND').waitFor({ timeout: 5000 });
        assert(state.projectGets === 0, 'historical-unbound conversation silently looked up or inferred a Project on open');
        assert(state.conversationPosts.length === 0, 'historical-unbound conversation was silently rebound through conversation creation');
      });
    });
  });

  console.log(JSON.stringify({
    desktopExistingProjectSelection: true,
    reasonPayloadPreserved: true,
    mobileBoundProjectNameResolved: true,
    mobileProjectCreation: true,
    mobileUsesBuildLanguage: true,
    repositoryShorthandNormalized: true,
    canonicalProjectIdOnly: true,
    staleProjectFailsClosed: true,
    historicalUnboundVisibleWithoutGuess: true,
    mobileGeometryPreserved: true,
  }, null, 2));
} finally {
  await browser?.close();
  await close(staticApp).catch(() => undefined);
}
