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

const supabaseUser = {
  id: 'supabase-google-owner',
  aud: 'authenticated',
  email: owner.email,
  app_metadata: { provider: 'google', providers: ['google'] },
  user_metadata: { full_name: owner.display_name },
  created_at: '2026-08-21T00:00:00Z',
};

const conversation = {
  id: '11111111-1111-4111-8111-111111111111',
  title: 'New conversation',
  mode: 'reason',
  status: 'ACTIVE',
  spec_id: 'P2-V0.10.0',
  created_at: '2026-08-21T00:00:00Z',
  updated_at: '2026-08-21T00:00:00Z',
  messages: [],
};

let authenticated = false;
let googleExchangeAuthorization = '';
let sessionMarkerObserved = false;
let sessionDeleteObserved = false;
let authorizeRequestObserved = false;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await context.newPage();
const browserErrors = [];
page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`));
page.on('console', (message) => {
  if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`);
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
    assert(requestUrl.searchParams.get('provider') === 'google', 'OAuth provider was not Google');
    assert(requestUrl.searchParams.get('code_challenge_method') === 's256', 'OAuth did not use PKCE S256');
    assert(Boolean(requestUrl.searchParams.get('code_challenge')), 'OAuth code challenge was missing');
    const redirectTo = requestUrl.searchParams.get('redirect_to');
    assert(redirectTo === `${origin}/auth/callback`, `Unexpected OAuth redirect target: ${redirectTo}`);
    authorizeRequestObserved = true;
    // A 204 navigation does not replace the active document. This models the
    // consent boundary without destroying the Parallax-origin sessionStorage
    // that Supabase intentionally uses for the PKCE verifier.
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
        refresh_token: 'supabase-transient-refresh',
        user: supabaseUser,
      }),
    });
    return;
  }

  if (pathname === '/auth/v1/user') {
    await route.fulfill({
      status: 200,
      headers: supabaseCorsHeaders({ 'content-type': 'application/json' }),
      body: body(supabaseUser),
    });
    return;
  }

  if (pathname === '/auth/v1/logout') {
    await route.fulfill({ status: 204, headers: supabaseCorsHeaders(), body: '' });
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
      await route.fulfill({
        status: authenticated ? 200 : 401,
        contentType: 'application/json',
        body: body(authenticated ? { authenticated: true } : { detail: 'Authentication required' }),
      });
      return;
    }
    if (apiPath === '/v1/session/google' && request.method() === 'POST') {
      googleExchangeAuthorization = request.headers().authorization ?? '';
      authenticated = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          'set-cookie': 'parallax_session=mock-signed-session; Path=/; HttpOnly; Secure; SameSite=Lax',
        },
        body: body({ authenticated: true, expires_at: '2026-08-22T00:00:00Z' }),
      });
      return;
    }
    if (apiPath === '/v1/session' && request.method() === 'DELETE') {
      authenticated = false;
      sessionDeleteObserved = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          'set-cookie': 'parallax_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0',
        },
        body: body({ authenticated: false }),
      });
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

  const relative = pathname === '/' || pathname === '/auth/callback'
    ? 'index.html'
    : pathname.replace(/^\/+/, '');
  const target = normalize(join(root, relative));
  if (!target.startsWith(normalize(root)) || !existsSync(target)) {
    await route.fulfill({ status: 404, body: 'not found' });
    return;
  }
  await route.fulfill({
    status: 200,
    contentType: mime[extname(target)] ?? 'application/octet-stream',
    body: readFileSync(target),
  });
});

try {
  await page.goto(origin, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Continue with Google' }).waitFor({ timeout: 10000 });
  const sharedCredentialVisible = await page.getByPlaceholder('Access credential').isVisible().catch(() => false);
  assert(!sharedCredentialVisible, 'Shared access credential field remained visible');

  const authorizeRequest = page.waitForRequest((request) => request.url().startsWith(`${supabaseOrigin}/auth/v1/authorize`));
  await page.getByRole('button', { name: 'Continue with Google' }).click();
  await authorizeRequest;
  await page.waitForTimeout(100);
  assert(authorizeRequestObserved, 'Supabase Google authorization request was not observed');

  await page.goto(`${origin}/auth/callback?code=mock-google-code`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Message Parallax').waitFor({ timeout: 20000 });
  await page.getByRole('button', { name: 'Parallax access menu' }).waitFor({ timeout: 5000 });

  assert(googleExchangeAuthorization === 'Bearer supabase-transient-token', 'Parallax API did not receive the transient Supabase token for exchange');
  assert(sessionMarkerObserved, 'Authenticated browser traffic did not use the Parallax session marker');
  assert(page.url() === `${origin}/`, `OAuth callback URL was not cleaned: ${page.url()}`);

  const storedSecrets = await page.evaluate(() => ({
    local: Object.values(localStorage),
    session: Object.values(sessionStorage),
  }));
  assert(!storedSecrets.local.some((value) => value.includes('supabase-transient-token')), 'Supabase access token persisted in localStorage');
  assert(!storedSecrets.session.some((value) => value.includes('supabase-transient-token')), 'Supabase access token persisted in sessionStorage');

  await page.getByRole('button', { name: 'Parallax access menu' }).click();
  await page.getByText('Authorized people').waitFor();
  await page.getByText(owner.email).first().waitFor();
  await page.getByRole('button', { name: 'Sign out of Parallax' }).click();
  await page.getByRole('button', { name: 'Continue with Google' }).waitFor({ timeout: 10000 });
  assert(sessionDeleteObserved, 'Parallax session logout was not sent to the API');

  const unexpectedErrors = browserErrors.filter((entry) => !entry.includes('favicon'));
  assert(unexpectedErrors.length === 0, `Hosted Google auth browser errors: ${unexpectedErrors.join(' | ')}`);

  console.log(JSON.stringify({
    googleAuthorizeRequest: authorizeRequestObserved,
    pkce: true,
    transientSupabaseToken: true,
    parallaxSessionExchange: true,
    sessionMarkerObserved,
    ownerAccessPanel: true,
    logout: sessionDeleteObserved,
  }, null, 2));
} finally {
  await browser.close();
}
