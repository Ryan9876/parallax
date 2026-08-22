const GUARD_STYLE_ID = 'parallax-mobile-viewport-guard';
const KEYBOARD_REDUCTION_THRESHOLD = 120;

type GuardedWindow = Window & {
  __PARALLAX_MOBILE_VIEWPORT_GUARD__?: boolean;
};

type RootBaseline = {
  height: string;
  transform: string;
  transformOrigin: string;
};

function isEditable(target: EventTarget | null): target is HTMLElement {
  return target instanceof HTMLElement && target.matches(
    'input:not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"]), textarea, [contenteditable="true"]',
  );
}

function installMobileInputSizing() {
  if (document.getElementById(GUARD_STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = GUARD_STYLE_ID;
  style.textContent = `
    @media (max-width: 759px) {
      #root input,
      #root textarea,
      #root [contenteditable="true"] {
        font-size: 16px !important;
      }
    }
  `;
  document.head.appendChild(style);
}

export function installMobileViewportGuard() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  const guardedWindow = window as GuardedWindow;
  if (guardedWindow.__PARALLAX_MOBILE_VIEWPORT_GUARD__) return;
  guardedWindow.__PARALLAX_MOBILE_VIEWPORT_GUARD__ = true;

  installMobileInputSizing();

  let focusedEditable = isEditable(document.activeElement);
  let baseline: RootBaseline | null = null;
  let applied = false;
  let frame = 0;

  const restore = (root: HTMLElement) => {
    if (!applied || !baseline) return;
    root.style.height = baseline.height;
    root.style.transform = baseline.transform;
    root.style.transformOrigin = baseline.transformOrigin;
    delete root.dataset.parallaxKeyboardVisible;
    baseline = null;
    applied = false;
  };

  const apply = () => {
    frame = 0;
    const root = document.getElementById('root');
    const viewport = window.visualViewport;
    if (!root || !viewport) return;

    const layoutHeight = window.innerHeight;
    const viewportReduction = Math.max(0, layoutHeight - viewport.height);
    const bottomOcclusion = Math.max(0, layoutHeight - (viewport.height + viewport.offsetTop));
    const keyboardLikely = focusedEditable
      && Math.max(viewportReduction, bottomOcclusion) >= KEYBOARD_REDUCTION_THRESHOLD;

    if (!keyboardLikely) {
      restore(root);
      return;
    }

    if (!applied) {
      baseline = {
        height: root.style.height,
        transform: root.style.transform,
        transformOrigin: root.style.transformOrigin,
      };
      applied = true;
    }

    root.style.height = `${Math.round(viewport.height)}px`;
    root.style.transform = `translateY(${Math.round(viewport.offsetTop)}px)`;
    root.style.transformOrigin = 'top left';
    root.dataset.parallaxKeyboardVisible = 'true';
  };

  const schedule = () => {
    if (frame) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(apply);
  };

  const onFocusIn = (event: FocusEvent) => {
    if (!isEditable(event.target)) return;
    focusedEditable = true;
    schedule();
    window.setTimeout(schedule, 60);
    window.setTimeout(schedule, 240);
  };

  const onFocusOut = () => {
    window.setTimeout(() => {
      focusedEditable = isEditable(document.activeElement);
      schedule();
    }, 40);
  };

  document.addEventListener('focusin', onFocusIn);
  document.addEventListener('focusout', onFocusOut);
  window.visualViewport?.addEventListener('resize', schedule);
  window.visualViewport?.addEventListener('scroll', schedule);
  window.addEventListener('resize', schedule);
  window.addEventListener('orientationchange', schedule);
}

installMobileViewportGuard();
