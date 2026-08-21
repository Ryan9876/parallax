import { createClient, type SupportedStorage } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.EXPO_PUBLIC_PARALLAX_SUPABASE_URL
  ?? 'https://kjyenifnfjqnzfgshpwg.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = process.env.EXPO_PUBLIC_PARALLAX_SUPABASE_PUBLISHABLE_KEY
  ?? 'sb_publishable_r2rze_hNPMXthGCGW4hRHg_ajlu6INo';

const oauthStorage: SupportedStorage = {
  getItem: (key) => globalThis.sessionStorage?.getItem(key) ?? null,
  setItem: (key, value) => { globalThis.sessionStorage?.setItem(key, value); },
  removeItem: (key) => { globalThis.sessionStorage?.removeItem(key); },
};

const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    flowType: 'pkce',
    persistSession: false,
    autoRefreshToken: false,
    detectSessionInUrl: false,
    storage: oauthStorage,
  },
});

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
  const redirectTo = `${globalThis.location.origin}/auth/callback`;
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
      scopes: 'openid email profile',
      skipBrowserRedirect: true,
      queryParams: {
        prompt: 'select_account',
      },
    },
  });
  if (error) throw error;
  if (!data.url) throw new Error('Google sign-in could not be started');
  globalThis.location.assign(data.url);
}

export async function exchangeGoogleCallback(): Promise<string> {
  if (typeof globalThis.location === 'undefined') {
    throw new Error('Google callback is only available in a browser');
  }
  const url = new URL(globalThis.location.href);
  const providerError = url.searchParams.get('error_description') || url.searchParams.get('error');
  if (providerError) throw new Error(providerError);
  const code = url.searchParams.get('code');
  if (!code) throw new Error('Google callback did not include an authorization code');

  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) throw error;
  const accessToken = data.session?.access_token?.trim();
  if (!accessToken) throw new Error('Google sign-in did not return a usable session');
  return accessToken;
}

export async function clearTransientGoogleSession(): Promise<void> {
  try {
    await supabase.auth.signOut({ scope: 'local' });
  } catch {
    // The Parallax HttpOnly session is authoritative after exchange.
  }
}

export function clearOAuthCallbackUrl(): void {
  if (typeof globalThis.history === 'undefined' || typeof globalThis.location === 'undefined') return;
  globalThis.history.replaceState({}, '', `${globalThis.location.origin}/`);
}
