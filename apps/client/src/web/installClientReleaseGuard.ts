const RELEASE_CHECK_INTERVAL_MS = 60_000;
const RELEASE_CHECK_QUERY = '__parallax_release_check';
const UPDATE_BANNER_ID = 'parallax-client-update-banner';

type ReleaseGuardGlobal = typeof globalThis & {
  __PARALLAX_CLIENT_RELEASE_GUARD_INSTALLED__?: boolean;
};

function appAssetSignature(documentRef: Document): string | null {
  const assets = Array.from(documentRef.querySelectorAll('script[src], link[rel="stylesheet"][href]'))
    .map((node) => {
      const raw = node instanceof HTMLScriptElement
        ? node.getAttribute('src')
        : node instanceof HTMLLinkElement
          ? node.getAttribute('href')
          : null;
      if (!raw) return null;
      try {
        const url = new URL(raw, globalThis.location.origin);
        if (url.origin !== globalThis.location.origin) return null;
        return `${node.tagName.toLowerCase()}:${url.pathname}`;
      } catch {
        return null;
      }
    })
    .filter((value): value is string => Boolean(value))
    .sort();

  return assets.length ? assets.join('|') : null;
}

function showUpdateBanner() {
  if (document.getElementById(UPDATE_BANNER_ID) || !document.body) return;

  const banner = document.createElement('div');
  banner.id = UPDATE_BANNER_ID;
  banner.setAttribute('role', 'status');
  banner.setAttribute('aria-live', 'polite');
  Object.assign(banner.style, {
    position: 'fixed',
    zIndex: '2147483647',
    top: 'max(12px, env(safe-area-inset-top))',
    left: '50%',
    transform: 'translateX(-50%)',
    width: 'min(560px, calc(100vw - 24px))',
    boxSizing: 'border-box',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    padding: '12px 14px',
    border: '1px solid rgba(0, 132, 135, 0.34)',
    borderRadius: '16px',
    background: 'rgba(251, 247, 238, 0.98)',
    color: '#172024',
    boxShadow: '0 14px 36px rgba(23, 32, 36, 0.18)',
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  });

  const copy = document.createElement('div');
  copy.style.minWidth = '0';

  const title = document.createElement('div');
  title.textContent = 'Parallax was updated';
  Object.assign(title.style, {
    fontSize: '14px',
    lineHeight: '18px',
    fontWeight: '800',
  });

  const detail = document.createElement('div');
  detail.textContent = 'Refresh to keep this screen on the current client version.';
  Object.assign(detail.style, {
    marginTop: '2px',
    fontSize: '12px',
    lineHeight: '17px',
    color: '#626664',
  });

  const refresh = document.createElement('button');
  refresh.type = 'button';
  refresh.textContent = 'Refresh now';
  refresh.setAttribute('aria-label', 'Refresh Parallax to the current version');
  Object.assign(refresh.style, {
    flexShrink: '0',
    minWidth: '96px',
    minHeight: '44px',
    padding: '0 14px',
    border: '1px solid rgba(0, 132, 135, 0.34)',
    borderRadius: '12px',
    background: '#D4EBE7',
    color: '#006E70',
    font: 'inherit',
    fontSize: '12px',
    fontWeight: '800',
    cursor: 'pointer',
  });
  refresh.addEventListener('click', () => globalThis.location.reload());

  copy.append(title, detail);
  banner.append(copy, refresh);
  document.body.appendChild(banner);
}

function installClientReleaseGuard() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  const globalRef = globalThis as ReleaseGuardGlobal;
  if (globalRef.__PARALLAX_CLIENT_RELEASE_GUARD_INSTALLED__) return;
  globalRef.__PARALLAX_CLIENT_RELEASE_GUARD_INSTALLED__ = true;

  const loadedSignature = appAssetSignature(document);
  if (!loadedSignature) return;

  let checking = false;
  let stale = false;

  const check = async () => {
    if (checking || stale) return;
    checking = true;
    try {
      const url = new URL('/index.html', globalThis.location.origin);
      url.searchParams.set(RELEASE_CHECK_QUERY, String(Date.now()));
      const response = await globalThis.fetch(url.toString(), {
        method: 'GET',
        cache: 'no-store',
        credentials: 'same-origin',
        headers: { Accept: 'text/html' },
      });
      if (!response.ok) return;
      const contentType = response.headers.get('content-type') ?? '';
      if (!contentType.toLowerCase().includes('text/html')) return;

      const nextDocument = new DOMParser().parseFromString(await response.text(), 'text/html');
      const nextSignature = appAssetSignature(nextDocument);
      if (!nextSignature || nextSignature === loadedSignature) return;

      stale = true;
      showUpdateBanner();
    } catch {
      // Release detection is advisory. Network failures must not disrupt the active client.
    } finally {
      checking = false;
    }
  };

  const onVisible = () => {
    if (document.visibilityState === 'visible') void check();
  };

  window.addEventListener('focus', () => { void check(); });
  window.addEventListener('pageshow', () => { void check(); });
  document.addEventListener('visibilitychange', onVisible);
  globalThis.setInterval(() => { void check(); }, RELEASE_CHECK_INTERVAL_MS);
}

installClientReleaseGuard();
