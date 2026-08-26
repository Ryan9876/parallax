import { chromium } from 'playwright';
import { existsSync, readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const origin = 'https://parallax.test';
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

function body(payload) {
  return JSON.stringify(payload);
}

const owner = {
  id: '99999999-9999-4999-8999-999999999999',
  email: 'owner@example.test',
  display_name: 'Parallax Owner',
  avatar_url: null,
  role: 'owner',
  status: 'active',
  auth_method: 'google',
  bound: true,
  created_at: '2026-08-21T00:00:00Z',
  updated_at: '2026-08-21T00:00:00Z',
  last_login_at: '2026-08-21T00:00:00Z',
};

const conversation = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'Session expiry regression',
  mode: 'reason',
  status: 'ACTIVE',
  spec_id: 'P2-V0.11.1',
  project_id: null,
  project_binding_status: 'HISTORICAL_UNBOUND',
  created_at: '2026-08-21T00:00:00Z',
  updated_at: '2026-08-21T00:00:00Z',
  messages: [],
};

let authenticated = true;
let sessionDeleteObserved = false;
let accessUsersRequests = 0;
let unauthorizedGenericRequests = 0;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
const page = await context.newPage();
const browserErrors = [];
page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`);
});

await page.route(`${origin}/**`, async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  const pathname = url.pathname;

  if (pathname.startsWith('/p2-api/')) {
    const apiPath = pathname.slice('/p2-api'.length);

    if (apiPath === '/v1/session' && request.method() === 'GET') {
      await route.fulfill({
        status: authenticated ? 200 : 401,
        contentType: 'application/json',
        body: body(authenticated ? { authenticated: true } : { detail: 'Authentication required' }),
      });
      return;
    }
    if (apiPath === '/v1/session' && request.method() === 'DELETE') {
      sessionDeleteObserved = true;
      authenticated = false;
      await route.fulfill({ status: 200, contentType: 'application/json', body: body({ authenticated: false }) });
      return;
    }
    if (apiPath === '/v1/access/me' && request.method() === 'GET') {
      await route.fulfill({
        status: authenticated ? 200 : 401,
        contentType: 'application/json',
        body: body(authenticated ? owner : { detail: 'Authentication required' }),
      });
      return;
    }
    if (apiPath === '/v1/access/users' && request.method() === 'GET') {
      accessUsersRequests += 1;
      if (!authenticated) unauthorizedGenericRequests += 1;
      await route.fulfill({
        status: authenticated ? 200 : 401,
        contentType: 'application/json',
        body: body(authenticated ? [owner] : { detail: 'Authentication required' }),
      });
      return;
    }
    if (apiPath === '/v1/conversations' && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: body([conversation]) });
      return;
    }
    if (apiPath === `/v1/conversations/${conversation.id}/work-specifications/latest` && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: 'null' });
      return;
    }
    if (apiPath === `/v1/conversations/${conversation.id}/work-specifications/approved` && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: 'null' });
      return;
    }
    if (apiPath === `/v1/engineering-runs/conversation/${conversation.id}/latest` && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: 'null' });
      return;
    }
    await route.fulfill({ status: 404, contentType: 'application/json', body: body({ detail: 'mock route not found', apiPath }) });
    return;
  }

  const relative = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const target = normalize(join(root, relative));
  if (!target.startsWith(normalize(root)) || !existsSync(target)) {
    await route.fulfill({ status: 404, body: 'not found' });
    return;
  }
  await route.fulfill({ status: 200, contentType: mime[extname(target)] ?? 'application/octet-stream', body: readFileSync(target) });
});

try {
  await page.goto(origin, { waitUntil: 'networkidle' });
  await page.getByLabel('Message Parallax').waitFor({ timeout: 10000 });
  const accountMenu = page.getByRole('button', { name: 'Parallax access menu' });
  await accountMenu.waitFor({ timeout: 5000 });

  authenticated = false;
  await accountMenu.click();
  await page.getByRole('button', { name: 'Continue with Google' }).waitFor({ timeout: 10000 });

  assert(accessUsersRequests >= 1, 'Session-expiry regression did not trigger a generic authenticated API request');
  assert(unauthorizedGenericRequests >= 1, 'Generic authenticated API request did not receive the simulated expired-session 401');
  assert(!(await accountMenu.isVisible().catch(() => false)), 'Stale authenticated account UI remained visible after generic 401');
  assert(!(await page.getByLabel('Message Parallax').isVisible().catch(() => false)), 'Workspace remained visually authenticated after generic 401');
  assert(!sessionDeleteObserved, 'Session-expiry recovery incorrectly performed explicit sign-out');

  const expected401s = browserErrors.filter((entry) => entry.includes('401 (Unauthorized)'));
  const unexpectedErrors = browserErrors.filter((entry) => !entry.includes('favicon') && !entry.includes('401 (Unauthorized)'));
  assert(unexpectedErrors.length === 0, `Session-expiry browser errors: ${unexpectedErrors.join(' | ')}`);

  console.log(JSON.stringify({
    genericAuthenticated401Observed: unauthorizedGenericRequests >= 1,
    returnedToLoginGate: true,
    profileCleared: true,
    workspaceUnmounted: true,
    explicitSignOutNotInvoked: !sessionDeleteObserved,
    expected401s: expected401s.length,
  }, null, 2));
} finally {
  await browser.close();
}
