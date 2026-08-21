const SUPABASE_URL = process.env.EXPO_PUBLIC_PARALLAX_SUPABASE_URL
  ?? 'https://kjyenifnfjqnzfgshpwg.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = process.env.EXPO_PUBLIC_PARALLAX_SUPABASE_PUBLISHABLE_KEY
  ?? 'sb_publishable_r2rze_hNPMXthGCGW4hRHg_ajlu6INo';
const PKCE_STORAGE_KEY = 'parallax:google:pkce-verifier';

function base64Url(bytes: Uint8Array): string {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

function randomVerifier(): string {
  const bytes = new Uint8Array(48);
  globalThis.crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

async function challengeFor(verifier: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(verifier),
  );
  return base64Url(new Uint8Array(digest));
}

export function isHostedHttpsWeb(): boolean {
  return typeof globalThis.location !== 'undefined' && globalThis.location.protocol === 'https:';
}

export function isOAuthCallback(): boolean {
  if (typeof globalThis.location === 'undefined') return false;
  const url = new URL(globalThis.location.href);
  return url.pathname === '/auth/callback' || url.searchParams.has('code') || url.searchParams.has('error');
}

export async function beginGoogleSignIn(): Promise<void> {
  if (!isHostedHttpsWeb()) return;
  if (!globalThis.crypto?.subtle || !globalThis.sessionStorage) {
    throw new Error('This browser cannot start secure Google sign-in');
  }

  const verifier = randomVerifier();
  const challenge = await challengeFor(verifier);
  globalThis.sessionStorage.setItem(PKCE_STORAGE_KEY, verifier);

  const redirectTo = `${globalThis.location.origin}/auth/callback`;
  const authorizeUrl = new URL('/auth/v1/authorize', SUPABASE_URL);
  authorizeUrl.searchParams.set('provider', 'google');
  authorizeUrl.searchParams.set('redirect_to', redirectTo);
  authorizeUrl.searchParams.set('scopes', 'openid email profile');
  authorizeUrl.searchParams.set('code_challenge', challenge);
  authorizeUrl.searchParams.set('code_challenge_method', 's256');
  authorizeUrl.searchParams.set('prompt', 'select_account');

  globalThis.location.assign(authorizeUrl.toString());
}

export async function exchangeGoogleCallback(): Promise<string> {
  if (typeof globalThis.location === 'undefined' || !globalThis.sessionStorage) {
    throw new Error('Google callback is only available in a browser');
  }

  const url = new URL(globalThis.location.href);
  const providerError = url.searchParams.get('error_description') || url.searchParams.get('error');
  if (providerError) throw new Error(providerError);

  const code = url.searchParams.get('code');
  if (!code) throw new Error('Google callback did not include an authorization code');

  const verifier = globalThis.sessionStorage.getItem(PKCE_STORAGE_KEY)?.trim();
  if (!verifier) throw new Error('Google sign-in verifier is missing or expired');

  try {
    const response = await globalThis.fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=pkce`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_PUBLISHABLE_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ auth_code: code, code_verifier: verifier }),
    });

    if (!response.ok) {
      let detail = `Google sign-in exchange failed (${response.status})`;
      try {
        const payload = await response.json() as { msg?: string; message?: string; error_description?: string };
        detail = payload.error_description || payload.message || payload.msg || detail;
      } catch {
        // Preserve the status fallback when Supabase does not return JSON.
      }
      throw new Error(detail);
    }

    const payload = await response.json() as { access_token?: string };
    const accessToken = payload.access_token?.trim();
    if (!accessToken) throw new Error('Google sign-in did not return a usable session');
    return accessToken;
  } finally {
    globalThis.sessionStorage.removeItem(PKCE_STORAGE_KEY);
  }
}

export async function clearTransientGoogleSession(): Promise<void> {
  globalThis.sessionStorage?.removeItem(PKCE_STORAGE_KEY);
}

export function clearOAuthCallbackUrl(): void {
  if (typeof globalThis.history === 'undefined' || typeof globalThis.location === 'undefined') return;
  globalThis.history.replaceState({}, '', `${globalThis.location.origin}/`);
}
