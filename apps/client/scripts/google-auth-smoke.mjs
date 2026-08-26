import { chromium } from 'playwright';
import { existsSync, readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const origin = 'https://parallax.test';
const supabaseOrigin = 'https://kjyenifnfjqnzfgshpwg.supabase.co';
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

function body(route) {
  return JSON.stringify(route);
}

function overlaps(a, b) {
  return a.x < b.x + b.width
    && a.x + a.width > b.x
    && a.y < b.y + b.height
    && a.y + a.height > b.y;
}

function supabaseCorsHeaders(extra = {}) {
  return {
    'access-control-allow-origin': origin,
    'access-control-allow-credentials': 'true',
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'access-control-allow-headers': 'apikey,authorization,content-type,x-client-info,x-supabase-api-version',
    ...extra,
  };
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
  title: 'Mobile layout check',
  mode: 'reason',
  status: 'ACTIVE',
  spec_id: 'P2-V0.11.1',
  created_at: '2026-08-21T00:00:00Z',
  updated_at: '2026-08-21T00:00:00Z',
  messages: [
    {
      id: 'mobile-user',
      role: 'user',
      content: 'Hello',
      status: 'complete',
      created_at: '2026-08-21T00:00:00Z',
    },
    {
      id: 'mobile-assistant',
      role: 'assistant',
      content: 'Hello! How can I help you today?',
      status: 'complete',
      created_at: '2026-08-21T00:00:01Z',
    },
  ],
};

let authenticated = false;
let googleExchangeAuthorization = '';
let sessionMarkerObserved = false;
let sessionDeleteObserved = false;
const observedRequests = [];

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
const page = await context.newPage();
const browserErrors = [];
page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`);
});
page.on('request', (request) => {
  const url = new URL(request.url());
  if (url.origin === supabaseOrigin || url.origin === origin) {
    observedRequests.push(`${request.method()} ${url.origin}${url.pathname}${url.search}`);
  }
});

await page.route(`${supabaseOrigin}/auth/v1/**`, async (route) => {
  const request = route.request();
  const requestUrl = new URL(request.url());
  const pathname = requestUrl.pathname;

  if (request.method() === 'OPTIONS') {
    await route.fulfill({ status: 204, headers: supabaseCorsHeaders(), body: '' });
    return;
  }

  if (pathname === '/auth/v1/authorize') {
    await route.fulfill({ status: 204, body: '' });
    return;
  }

  if (pathname === '/auth/v1/token') {
    assert(requestUrl.searchParams.get('grant_type') === 'pkce', 'Supabase callback exchange did not use PKCE grant');
    const requestBody = request.postData() ?? '';
    assert(requestBody.includes('mock-google-code'), 'Supabase token exchange did not contain callback code');
    assert(requestBody.includes('code_verifier'), 'Supabase token exchange did not contain PKCE verifier');
    await route.fulfill({
      status: 200,
      headers: supabaseCorsHeaders({ 'content-type': 'application/json' }),
      body: body({
        access_token: 'supabase-transient-token',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    });
    return;
  }

  await route.fulfill({
    status: 404,
    headers: supabaseCorsHeaders({ 'content-type': 'application/json' }),
    body: body({ error: 'unmocked Supabase auth route', path: pathname }),
  });
});

await page.route(`${origin}/**`, async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  const pathname = url.pathname;

  if (pathname.startsWith('/p2-api/')) {
    const apiPath = pathname.slice('/p2-api'.length);
    sessionMarkerObserved ||= request.headers()['x-parallax-session'] === '1';

    if (apiPath === '/v1/session' && request.method() === 'GET') {
      await route.fulfill({ status: authenticated ? 200 : 401, contentType: 'application/json', body: body(authenticated ? { authenticated: true } : { detail: 'Authentication required' }) });
      return;
    }
    if (apiPath === '/v1/session/google' && request.method() === 'POST') {
      googleExchangeAuthorization = request.headers().authorization ?? '';
      authenticated = true;
      await route.fulfill({ status: 200, contentType: 'application/json', headers: { 'set-cookie': 'parallax_session=mock-signed-session; Path=/; HttpOnly; Secure; SameSite=Lax' }, body: body({ authenticated: true, expires_at: '2026-08-22T00:00:00Z' }) });
      return;
    }
    if (apiPath === '/v1/session' && request.method() === 'DELETE') {
      authenticated = false;
      sessionDeleteObserved = true;
      await route.fulfill({ status: 200, contentType: 'application/json', headers: { 'set-cookie': 'parallax_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0' }, body: body({ authenticated: false }) });
      return;
    }
    if (apiPath === '/v1/access/me' && request.method() === 'GET') {
      await route.fulfill({ status: authenticated ? 200 : 401, contentType: 'application/json', body: body(authenticated ? owner : { detail: 'Authentication required' }) });
      return;
    }
    if (apiPath === '/v1/access/users' && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: body([owner]) });
      return;
    }
    if (apiPath === '/v1/conversations' && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: body([conversation]) });
      return;
    }
    if (apiPath === `/v1/conversations/${conversation.id}` && request.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: body(conversation) });
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
    await route.fulfill({ status: 404, contentType: 'application/json', body: body({ detail: 'mock route not found' }) });
    return;
  }

  const relative = pathname === '/' || pathname === '/auth/callback' ? 'index.html' : pathname.replace(/^\/+/, '');
  const target = normalize(join(root, relative));
  if (!target.startsWith(normalize(root)) || !existsSync(target)) {
    await route.fulfill({ status: 404, body: 'not found' });
    return;
  }
  await route.fulfill({ status: 200, contentType: mime[extname(target)] ?? 'application/octet-stream', body: readFileSync(target) });
});

try {
  await page.goto(origin, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Continue with Google' }).waitFor({ timeout: 10000 });
  assert(!(await page.getByPlaceholder('Access credential').isVisible().catch(() => false)), 'Shared access credential field remained visible');

  const authorizeRequestPromise = page.waitForRequest((request) => request.url().startsWith(`${supabaseOrigin}/auth/v1/authorize`));
  await page.getByRole('button', { name: 'Continue with Google' }).click();
  const authorizeRequest = await authorizeRequestPromise;
  const authorizeUrl = new URL(authorizeRequest.url());
  assert(authorizeUrl.searchParams.get('provider') === 'google', 'OAuth provider was not Google');
  assert(authorizeUrl.searchParams.get('code_challenge_method') === 's256', 'OAuth did not use PKCE S256');
  assert(Boolean(authorizeUrl.searchParams.get('code_challenge')), 'OAuth code challenge was missing');
  assert(authorizeUrl.searchParams.get('redirect_to') === `${origin}/auth/callback`, `Unexpected OAuth redirect target: ${authorizeUrl.searchParams.get('redirect_to')}`);

  await page.goto(`${origin}/auth/callback?code=mock-google-code`, { waitUntil: 'domcontentloaded' });
  try {
    await page.getByLabel('Message Parallax').waitFor({ timeout: 20000 });
  } catch (error) {
    const diagnostics = await page.evaluate(() => ({ body: document.body.innerText.slice(0, 2000), sessionStorageKeys: Object.keys(sessionStorage), localStorageKeys: Object.keys(localStorage), href: location.href }));
    throw new Error(`Google callback did not reach the workspace. diagnostics=${JSON.stringify({ diagnostics, googleSessionExchangeObserved: Boolean(googleExchangeAuthorization), sessionMarkerObserved, observedRequests: observedRequests.slice(-30), browserErrors: browserErrors.slice(-20) })}`, { cause: error });
  }
  const accountMenu = page.getByRole('button', { name: 'Parallax access menu' });
  const mobileShell = page.getByTestId('mobile-guided-shell');
  const askButton = page.getByRole('button', { name: 'Ask mode' });
  const buildButton = page.getByRole('button', { name: 'Build mode' });
  const newConversationButton = page.getByRole('button', { name: 'New conversation' });
  const bottomNavigation = page.getByTestId('mobile-bottom-navigation');
  const composer = page.getByLabel('Message Parallax');
  await accountMenu.waitFor({ timeout: 5000 });
  await mobileShell.waitFor({ timeout: 5000 });
  await askButton.waitFor({ timeout: 5000 });
  await buildButton.waitFor({ timeout: 5000 });
  await newConversationButton.waitFor({ timeout: 5000 });
  await bottomNavigation.waitFor({ timeout: 5000 });

  const accountBox = await accountMenu.boundingBox();
  const askBox = await askButton.boundingBox();
  const buildBox = await buildButton.boundingBox();
  const newConversationBox = await newConversationButton.boundingBox();
  const navigationBox = await bottomNavigation.boundingBox();
  const composerBox = await composer.boundingBox();
  assert(accountBox && askBox && buildBox && newConversationBox && navigationBox && composerBox, 'Mobile authenticated-shell geometry was unavailable');
  assert(accountBox.height >= 44 && accountBox.width >= 44, `Mobile account launcher is smaller than a practical touch target: ${JSON.stringify(accountBox)}`);
  assert(accountBox.x >= 0 && accountBox.x + accountBox.width <= 390, `Mobile account launcher is clipped: ${JSON.stringify(accountBox)}`);
  assert(await page.getByLabel('Work specification', { exact: true }).count() === 0, 'Mobile authenticated Chat restored the retired inline Work Specification');
  assert(await page.getByRole('tab').count() === 3, 'Mobile authenticated workspace must expose exactly Chat, Build, and Project');
  assert(!overlaps(accountBox, askBox) && !overlaps(accountBox, buildBox), `Mobile account launcher overlaps Ask/Build controls: account=${JSON.stringify(accountBox)} ask=${JSON.stringify(askBox)} build=${JSON.stringify(buildBox)}`);
  assert(!overlaps(accountBox, newConversationBox), `Mobile account launcher overlaps new-conversation control: account=${JSON.stringify(accountBox)} newConversation=${JSON.stringify(newConversationBox)}`);
  assert(composerBox.y + composerBox.height <= navigationBox.y + 1, `Mobile authenticated composer overlaps bottom navigation: composer=${JSON.stringify(composerBox)} navigation=${JSON.stringify(navigationBox)}`);

  assert(googleExchangeAuthorization === 'Bearer supabase-transient-token', 'Parallax API did not receive the transient Supabase token for exchange');
  assert(sessionMarkerObserved, 'Authenticated browser traffic did not use the Parallax session marker');
  assert(page.url() === `${origin}/`, `OAuth callback URL was not cleaned: ${page.url()}`);

  const storedSecrets = await page.evaluate(() => ({ local: Object.values(localStorage), session: Object.values(sessionStorage), sessionKeys: Object.keys(sessionStorage) }));
  assert(!storedSecrets.local.some((value) => value.includes('supabase-transient-token')), 'Supabase access token persisted in localStorage');
  assert(!storedSecrets.session.some((value) => value.includes('supabase-transient-token')), 'Supabase access token persisted in sessionStorage');
  assert(!storedSecrets.sessionKeys.includes('parallax:google:pkce-verifier'), 'PKCE verifier remained after callback exchange');

  await accountMenu.click();
  await page.getByText('Authorized people').waitFor();
  await page.getByText(owner.email).first().waitFor();
  const accessPanelBox = await page.getByLabel('Parallax access panel').boundingBox();
  assert(accessPanelBox, 'Mobile access panel geometry was unavailable');
  assert(accessPanelBox.x >= 10, `Mobile access panel clipped left: ${JSON.stringify(accessPanelBox)}`);
  assert(accessPanelBox.x + accessPanelBox.width <= 380, `Mobile access panel clipped right: ${JSON.stringify(accessPanelBox)}`);

  await page.getByRole('button', { name: 'Sign out of Parallax' }).click();
  await page.getByRole('button', { name: 'Continue with Google' }).waitFor({ timeout: 10000 });
  assert(sessionDeleteObserved, 'Parallax session logout was not sent to the API');

  const authBoundaryErrors = browserErrors.filter((entry) => entry.includes('Failed to load resource: the server responded with a status of 401 (Unauthorized)'));
  assert(authBoundaryErrors.length >= 1, 'Unauthenticated browser session boundary did not surface the expected 401');
  const unexpectedErrors = browserErrors.filter((entry) => !entry.includes('favicon') && !entry.includes('Failed to load resource: the server responded with a status of 401 (Unauthorized)'));
  assert(unexpectedErrors.length === 0, `Hosted Google auth browser errors: ${unexpectedErrors.join(' | ')}`);

  console.log(JSON.stringify({
    googleAuthorizeRequest: true,
    pkce: true,
    transientSupabaseToken: true,
    parallaxSessionExchange: true,
    sessionMarkerObserved,
    ownerAccessPanel: true,
    mobileInlineWorkSpecificationRetired: true,
    mobilePrimaryNavigation: ['Chat', 'Build', 'Project'],
    mobileAccountTouchTarget: true,
    mobileAccountNoOverlap: true,
    mobileComposerClearOfNavigation: true,
    mobileAccessPanelFit: true,
    logout: sessionDeleteObserved,
    expectedAuthBoundary401s: authBoundaryErrors.length,
  }, null, 2));
} finally {
  await browser.close();
}
