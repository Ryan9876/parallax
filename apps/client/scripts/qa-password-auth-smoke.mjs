import { chromium } from 'playwright';
import { existsSync, readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('../dist/', import.meta.url).pathname;
const origin = 'https://parallax.test';
const supabaseOrigin = 'https://kjyenifnfjqnzfgshpwg.supabase.co';
const syntheticEmail = 'qa@example.test';
const syntheticPassword = 'Synthetic-only-1234';
const syntheticRecoveryPassword = 'Synthetic-reset-5678';
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

function json(value) {
  return JSON.stringify(value);
}

function cors(extra = {}) {
  return {
    'access-control-allow-origin': origin,
    'access-control-allow-credentials': 'true',
    'access-control-allow-methods': 'GET,POST,PUT,OPTIONS',
    'access-control-allow-headers': 'apikey,authorization,content-type',
    ...extra,
  };
}

const owner = {
  id: '99999999-9999-4999-8999-999999999999',
  email: syntheticEmail,
  display_name: 'QA Test Account',
  avatar_url: null,
  role: 'owner',
  status: 'active',
  auth_method: 'google',
  bound: true,
  created_at: '2026-08-29T00:00:00Z',
  updated_at: '2026-08-29T00:00:00Z',
  last_login_at: '2026-08-29T00:00:00Z',
};

let authenticated = false;
let qaTokenRequest = null;
let parallaxToken = '';
let recoveryRequest = null;
let passwordUpdate = null;

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 900 } });
const page = await context.newPage();
const pageErrors = [];
page.on('pageerror', (error) => pageErrors.push(error.message));

await page.route(`${supabaseOrigin}/auth/v1/**`, async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  if (request.method() === 'OPTIONS') {
    await route.fulfill({ status: 204, headers: cors(), body: '' });
    return;
  }
  if (url.pathname === '/auth/v1/token' && url.searchParams.get('grant_type') === 'password') {
    qaTokenRequest = { url: request.url(), body: JSON.parse(request.postData() ?? '{}') };
    await route.fulfill({
      status: 200,
      headers: cors({ 'content-type': 'application/json' }),
      body: json({ access_token: 'synthetic-supabase-access-token', refresh_token: 'must-not-persist' }),
    });
    return;
  }
  if (url.pathname === '/auth/v1/recover') {
    recoveryRequest = { url: request.url(), body: JSON.parse(request.postData() ?? '{}') };
    await route.fulfill({ status: 200, headers: cors({ 'content-type': 'application/json' }), body: '{}' });
    return;
  }
  if (url.pathname === '/auth/v1/user' && request.method() === 'PUT') {
    passwordUpdate = {
      url: request.url(),
      authorization: request.headers().authorization ?? '',
      body: JSON.parse(request.postData() ?? '{}'),
    };
    await route.fulfill({ status: 200, headers: cors({ 'content-type': 'application/json' }), body: json({ id: owner.id }) });
    return;
  }
  await route.fulfill({ status: 404, headers: cors({ 'content-type': 'application/json' }), body: json({ error: 'unmocked' }) });
});

await page.route(`${origin}/**`, async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  const pathname = url.pathname;
  if (pathname.startsWith('/p2-api/')) {
    const apiPath = pathname.slice('/p2-api'.length);
    if (apiPath === '/v1/session' && request.method() === 'GET') {
      await route.fulfill({ status: authenticated ? 200 : 401, contentType: 'application/json', body: json(authenticated ? { authenticated: true } : { detail: 'Authentication required' }) });
      return;
    }
    if (apiPath === '/v1/session/google' && request.method() === 'POST') {
      parallaxToken = request.headers().authorization ?? '';
      authenticated = true;
      await route.fulfill({ status: 200, contentType: 'application/json', body: json({ authenticated: true }) });
      return;
    }
    if (apiPath === '/v1/access/me' && request.method() === 'GET') {
      await route.fulfill({ status: authenticated ? 200 : 401, contentType: 'application/json', body: json(authenticated ? owner : { detail: 'Authentication required' }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: request.method() === 'GET' ? '[]' : '{}' });
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
  await page.getByRole('button', { name: 'Continue with Google' }).waitFor({ timeout: 10000 });
  assert(await page.getByLabel('QA email').count() === 0, 'Ordinary root exposed the QA email field');
  assert(await page.getByLabel('QA password').count() === 0, 'Ordinary root exposed the QA password field');
  assert(await page.getByRole('button', { name: 'Set or reset QA password' }).count() === 0, 'Ordinary root exposed QA recovery');

  await page.goto(`${origin}/?qa=1`, { waitUntil: 'networkidle' });
  await page.getByLabel('QA email').fill(syntheticEmail);
  await page.getByLabel('QA password').fill(syntheticPassword);
  await page.getByRole('button', { name: 'Sign in to QA account' }).click();
  await page.getByRole('button', { name: 'Parallax access menu' }).waitFor({ timeout: 10000 });

  assert(qaTokenRequest?.body?.email === syntheticEmail, 'QA sign-in did not send the normalized email to Supabase');
  assert(qaTokenRequest?.body?.password === syntheticPassword, 'QA sign-in did not send the password in the HTTPS request body');
  assert(!qaTokenRequest.url.includes(syntheticPassword), 'QA password leaked into the Supabase URL');
  assert(parallaxToken === 'Bearer synthetic-supabase-access-token', 'Existing Parallax Google-session exchange did not receive the transient Supabase token');

  const signInStorage = await page.evaluate(() => ({ local: Object.values(localStorage), session: Object.values(sessionStorage), href: location.href }));
  assert(!json(signInStorage).includes(syntheticPassword), 'QA password persisted in browser storage or URL');
  assert(!json(signInStorage).includes('synthetic-supabase-access-token'), 'Supabase access token persisted in browser storage or URL');
  assert(!json(signInStorage).includes('must-not-persist'), 'Supabase refresh token persisted in browser storage or URL');

  authenticated = false;
  await context.clearCookies();
  await page.goto(`${origin}/?qa=1`, { waitUntil: 'networkidle' });
  await page.getByLabel('QA email').fill(syntheticEmail);
  await page.getByRole('button', { name: 'Set or reset QA password' }).click();
  await page.getByText('If this is the authorized QA account').waitFor({ timeout: 5000 });
  assert(recoveryRequest?.body?.email === syntheticEmail, 'Recovery request did not send the QA email');
  assert(recoveryRequest?.body?.redirect_to === `${origin}/?qa=1`, 'Recovery request did not preserve the hidden QA return path');
  assert(!recoveryRequest.url.includes(syntheticEmail), 'Recovery email leaked into the request URL');

  await page.goto(`${origin}/?qa=1#access_token=synthetic-recovery-token&refresh_token=must-not-persist&type=recovery`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('New QA password').waitFor({ timeout: 10000 });
  assert(page.url() === `${origin}/?qa=1`, `Recovery fragment was not removed immediately: ${page.url()}`);
  await page.getByLabel('New QA password').fill(syntheticRecoveryPassword);
  await page.getByRole('button', { name: 'Save QA password' }).click();
  await page.getByText('Password saved. Sign in with the QA account below.').waitFor({ timeout: 5000 });

  assert(passwordUpdate?.authorization === 'Bearer synthetic-recovery-token', 'Password update did not use the transient recovery token');
  assert(passwordUpdate?.body?.password === syntheticRecoveryPassword, 'Password update did not send the new password in the HTTPS request body');
  assert(!passwordUpdate.url.includes(syntheticRecoveryPassword), 'New password leaked into the Supabase URL');
  const recoveryStorage = await page.evaluate(() => ({ local: Object.values(localStorage), session: Object.values(sessionStorage), href: location.href }));
  assert(!json(recoveryStorage).includes(syntheticRecoveryPassword), 'New password persisted in browser storage or URL');
  assert(!json(recoveryStorage).includes('synthetic-recovery-token'), 'Recovery access token persisted in browser storage or URL');
  assert(!json(recoveryStorage).includes('must-not-persist'), 'Recovery refresh token persisted in browser storage or URL');
  assert(pageErrors.length === 0, `QA auth browser errors: ${pageErrors.join(' | ')}`);

  console.log(JSON.stringify({
    ordinaryRootGoogleOnly: true,
    hiddenQaEntry: true,
    passwordBodyOnly: true,
    existingParallaxSessionExchange: true,
    recoveryEmail: true,
    recoveryFragmentCleared: true,
    passwordUpdate: true,
    noCredentialPersistence: true,
  }, null, 2));
} finally {
  await browser.close();
}
