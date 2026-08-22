const GUARD_STYLE_ID = 'parallax-mobile-viewport-guard';
const KEYBOARD_REDUCTION_THRESHOLD = 120;
const LIVE_EDGE_THRESHOLD = 120;

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

function installConversationLiveEdgeGuard(root: HTMLElement) {
  let activeThread: HTMLElement | null = null;
  let followLiveEdge = true;
  let followFrame = 0;
  let settleTimer = 0;

  const distanceFromEnd = (thread: HTMLElement) => Math.max(
    0,
    thread.scrollHeight - thread.clientHeight - thread.scrollTop,
  );

  const findConversationThread = () => {
    const response = root.querySelector<HTMLElement>('[aria-label="Parallax response"]');
    let current = response?.parentElement ?? null;
    while (current && current !== root) {
      const style = window.getComputedStyle(current);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') return current;
      current = current.parentElement;
    }
    return null;
  };

  const onThreadScroll = () => {
    if (!activeThread) return;
    followLiveEdge = distanceFromEnd(activeThread) < LIVE_EDGE_THRESHOLD;
  };

  const attachThread = () => {
    const next = findConversationThread();
    if (next === activeThread) return next;
    activeThread?.removeEventListener('scroll', onThreadScroll);
    activeThread = next;
    followLiveEdge = true;
    activeThread?.addEventListener('scroll', onThreadScroll, { passive: true });
    return activeThread;
  };

  const applyLiveEdge = () => {
    followFrame = 0;
    const thread = attachThread();
    if (!thread || !followLiveEdge) return;
    thread.scrollTop = thread.scrollHeight;
  };

  const scheduleLiveEdge = () => {
    if (followFrame) cancelAnimationFrame(followFrame);
    followFrame = requestAnimationFrame(() => {
      applyLiveEdge();
      requestAnimationFrame(applyLiveEdge);
    });
  };

  const scheduleSettledLiveEdge = () => {
    scheduleLiveEdge();
    if (settleTimer) window.clearTimeout(settleTimer);
    settleTimer = window.setTimeout(scheduleLiveEdge, 120);
  };

  const observer = new MutationObserver(() => {
    attachThread();
    if (followLiveEdge) scheduleSettledLiveEdge();
  });
  observer.observe(root, { subtree: true, childList: true, characterData: true });

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('[aria-label]') : null;
    const label = target?.getAttribute('aria-label') ?? '';
    if (label === 'Send message' || label === 'New conversation') {
      followLiveEdge = true;
    }
    if (
      label === 'Send message'
      || label === 'New conversation'
      || label === 'Expand work specification'
      || label === 'Collapse work specification'
      || label === 'Approve work specification'
      || label === 'Refresh work specification draft'
    ) {
      scheduleSettledLiveEdge();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.shiftKey || !isEditable(event.target)) return;
    if ((event.target as HTMLElement).getAttribute('aria-label') !== 'Message Parallax') return;
    followLiveEdge = true;
    scheduleSettledLiveEdge();
  });

  window.addEventListener('resize', scheduleSettledLiveEdge);
  window.addEventListener('orientationchange', scheduleSettledLiveEdge);
  attachThread();
  scheduleSettledLiveEdge();
}

export function installMobileViewportGuard() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  const guardedWindow = window as GuardedWindow;
  if (guardedWindow.__PARALLAX_MOBILE_VIEWPORT_GUARD__) return;
  guardedWindow.__PARALLAX_MOBILE_VIEWPORT_GUARD__ = true;

  installMobileInputSizing();

  const root = document.getElementById('root');
  if (root) installConversationLiveEdgeGuard(root);

  let focusedEditable = isEditable(document.activeElement);
  let baseline: RootBaseline | null = null;
  let applied = false;
  let frame = 0;

  const restore = (rootElement: HTMLElement) => {
    if (!applied || !baseline) return;
    rootElement.style.height = baseline.height;
    rootElement.style.transform = baseline.transform;
    rootElement.style.transformOrigin = baseline.transformOrigin;
    delete rootElement.dataset.parallaxKeyboardVisible;
    baseline = null;
    applied = false;
  };

  const apply = () => {
    frame = 0;
    const rootElement = document.getElementById('root');
    const viewport = window.visualViewport;
    if (!rootElement || !viewport) return;

    const layoutHeight = window.innerHeight;
    const viewportReduction = Math.max(0, layoutHeight - viewport.height);
    const bottomOcclusion = Math.max(0, layoutHeight - (viewport.height + viewport.offsetTop));
    const keyboardLikely = focusedEditable
      && Math.max(viewportReduction, bottomOcclusion) >= KEYBOARD_REDUCTION_THRESHOLD;

    if (!keyboardLikely) {
      restore(rootElement);
      return;
    }

    if (!applied) {
      baseline = {
        height: rootElement.style.height,
        transform: rootElement.style.transform,
        transformOrigin: rootElement.style.transformOrigin,
      };
      applied = true;
    }

    rootElement.style.height = `${Math.round(viewport.height)}px`;
    rootElement.style.transform = `translateY(${Math.round(viewport.offsetTop)}px)`;
    rootElement.style.transformOrigin = 'top left';
    rootElement.dataset.parallaxKeyboardVisible = 'true';
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
