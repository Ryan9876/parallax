const SUPABASE_URL = process.env.EXPO_PUBLIC_PARALLAX_SUPABASE_URL
  ?? 'https://kjyenifnfjqnzfgshpwg.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = process.env.EXPO_PUBLIC_PARALLAX_SUPABASE_PUBLISHABLE_KEY
  ?? 'sb_publishable_r2rze_hNPMXthGCGW4hRHg_ajlu6INo';

type AuthPayload = {
  access_token?: string;
};

function requireHostedQaBrowser(): void {
  if (
    typeof globalThis.location === 'undefined'
    || globalThis.location.protocol !== 'https:'
    || !globalThis.fetch
  ) {
    throw new Error('QA account access is available only on the secure hosted site.');
  }
}

function normalizedEmail(value: string): string {
  const candidate = value.trim().toLowerCase();
  if (!candidate || !candidate.includes('@')) {
    throw new Error('Enter the QA account email.');
  }
  return candidate;
}

function requiredPassword(value: string, options?: { newPassword?: boolean }): string {
  const newPassword = options?.newPassword === true;
  if (!value) throw new Error(newPassword ? 'Enter a new password.' : 'Enter the QA account password.');
  if (newPassword && value.length < 12) {
    throw new Error('Choose a new password with at least 12 characters.');
  }
  return value;
}

function supabaseHeaders(accessToken?: string): Record<string, string> {
  return {
    apikey: SUPABASE_PUBLISHABLE_KEY,
    'Content-Type': 'application/json',
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

export function isQaPasswordAccessRequested(): boolean {
  if (typeof globalThis.location === 'undefined') return false;
  const url = new URL(globalThis.location.href);
  if (url.searchParams.get('qa') === '1') return true;
  const fragment = new URLSearchParams(url.hash.replace(/^#/, ''));
  return fragment.get('type') === 'recovery' && Boolean(fragment.get('access_token'));
}

export function captureQaRecoveryToken(): string | null {
  if (typeof globalThis.location === 'undefined' || typeof globalThis.history === 'undefined') return null;
  const url = new URL(globalThis.location.href);
  const fragment = new URLSearchParams(url.hash.replace(/^#/, ''));
  const token = fragment.get('type') === 'recovery'
    ? fragment.get('access_token')?.trim() ?? ''
    : '';
  if (!token) return null;

  url.hash = '';
  url.searchParams.set('qa', '1');
  globalThis.history.replaceState({}, '', `${url.pathname}${url.search}`);
  return token;
}

export async function signInWithQaPassword(email: string, password: string): Promise<string> {
  requireHostedQaBrowser();
  const response = await globalThis.fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: supabaseHeaders(),
    body: JSON.stringify({
      email: normalizedEmail(email),
      password: requiredPassword(password),
    }),
  });
  if (!response.ok) throw new Error('The QA email or password was not accepted.');

  const payload = await response.json() as AuthPayload;
  const accessToken = payload.access_token?.trim();
  if (!accessToken) throw new Error('The QA account did not return a usable secure session.');
  return accessToken;
}

export async function requestQaPasswordRecovery(email: string): Promise<void> {
  requireHostedQaBrowser();
  const response = await globalThis.fetch(`${SUPABASE_URL}/auth/v1/recover`, {
    method: 'POST',
    headers: supabaseHeaders(),
    body: JSON.stringify({
      email: normalizedEmail(email),
      redirect_to: `${globalThis.location.origin}/?qa=1`,
    }),
  });
  if (!response.ok) {
    throw new Error('The recovery email could not be requested. Wait a moment and try again.');
  }
}

export async function updateQaPassword(accessToken: string, password: string): Promise<void> {
  requireHostedQaBrowser();
  const token = accessToken.trim();
  if (!token) throw new Error('This password-recovery link is missing or expired.');

  const response = await globalThis.fetch(`${SUPABASE_URL}/auth/v1/user`, {
    method: 'PUT',
    headers: supabaseHeaders(token),
    body: JSON.stringify({ password: requiredPassword(password, { newPassword: true }) }),
  });
  if (!response.ok) {
    throw new Error('The password could not be saved. Request a new recovery email and try again.');
  }
}
