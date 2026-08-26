const RESPONSE_SELECTOR = '[aria-label="Parallax response"]';
const INPUT_SELECTOR = '[aria-label="Message Parallax"]';
const SEND_SELECTOR = '[aria-label="Send message"]';
const NEW_CONVERSATION_SELECTOR = '[aria-label="New conversation"]';
const MOBILE_AMENDMENT_SELECTOR = '[data-testid="mobile-spec-amendment"]';
const LIVE_EDGE_THRESHOLD = 120;
const SETTLE_DELAY_MS = 120;

type GuardState = {
  thread: HTMLElement | null;
  armed: boolean;
  pinQueued: boolean;
  resizeObserver: ResizeObserver | null;
  scrollHandler: (() => void) | null;
  settleTimer: number;
};

const state: GuardState = {
  thread: null,
  armed: true,
  pinQueued: false,
  resizeObserver: null,
  scrollHandler: null,
  settleTimer: 0,
};

function isScrollable(element: HTMLElement) {
  const style = getComputedStyle(element);
  return style.overflowY === 'auto' || style.overflowY === 'scroll';
}

function findThread() {
  const responses = document.querySelectorAll<HTMLElement>(RESPONSE_SELECTOR);
  const anchor = responses.item(responses.length - 1);
  let current = anchor?.parentElement ?? null;

  while (current && current !== document.body) {
    if (isScrollable(current)) return current;
    current = current.parentElement;
  }
  return null;
}

function distanceFromEnd(thread: HTMLElement) {
  return Math.max(0, thread.scrollHeight - thread.clientHeight - thread.scrollTop);
}

function mobileRecoveryHasViewportPriority() {
  return window.innerWidth < 760 && Boolean(document.querySelector(MOBILE_AMENDMENT_SELECTOR));
}

function bindThread(thread: HTMLElement | null) {
  if (!thread || thread === state.thread) return;

  if (state.thread && state.scrollHandler) {
    state.thread.removeEventListener('scroll', state.scrollHandler);
  }
  state.resizeObserver?.disconnect();
  state.thread = thread;

  state.scrollHandler = () => {
    if (!state.thread) return;
    state.armed = distanceFromEnd(state.thread) < LIVE_EDGE_THRESHOLD;
  };
  thread.addEventListener('scroll', state.scrollHandler, { passive: true });

  state.resizeObserver = new ResizeObserver(() => {
    if (state.armed) queuePin();
  });
  state.resizeObserver.observe(thread);
}

function pinToLiveEdge() {
  if (mobileRecoveryHasViewportPriority()) return;
  const thread = findThread() ?? state.thread;
  bindThread(thread);
  if (!thread || !state.armed) return;
  thread.scrollTop = thread.scrollHeight;
}

function queuePin() {
  if (!state.pinQueued) {
    state.pinQueued = true;
    requestAnimationFrame(() => {
      state.pinQueued = false;
      pinToLiveEdge();
      requestAnimationFrame(pinToLiveEdge);
    });
  }

  if (state.settleTimer) window.clearTimeout(state.settleTimer);
  state.settleTimer = window.setTimeout(() => {
    state.settleTimer = 0;
    pinToLiveEdge();
  }, SETTLE_DELAY_MS);
}

function rearm() {
  state.armed = true;
  queuePin();
}

if (typeof document !== 'undefined') {
  const observer = new MutationObserver(() => {
    bindThread(findThread());
    if (state.armed) queuePin();
  });

  const start = () => {
    const root = document.getElementById('root');
    if (!root) {
      requestAnimationFrame(start);
      return;
    }

    observer.observe(root, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    document.addEventListener('click', (event) => {
      const target = event.target as Element | null;
      if (target?.closest(SEND_SELECTOR) || target?.closest(NEW_CONVERSATION_SELECTOR)) rearm();
    }, true);

    document.addEventListener('keydown', (event) => {
      const target = event.target as Element | null;
      if (event.key === 'Enter' && !event.shiftKey && target?.matches(INPUT_SELECTOR)) rearm();
    }, true);

    window.addEventListener('resize', () => {
      if (state.armed) queuePin();
    });
    window.addEventListener('orientationchange', () => {
      if (state.armed) queuePin();
    });

    bindThread(findThread());
    queuePin();
  };

  start();
}
