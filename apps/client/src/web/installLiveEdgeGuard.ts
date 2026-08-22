const RESPONSE_SELECTOR = '[aria-label="Parallax response"]';
const INPUT_SELECTOR = '[aria-label="Message Parallax"]';
const SEND_SELECTOR = '[aria-label="Send message"]';
const LIVE_EDGE_THRESHOLD = 120;

type GuardState = {
  thread: HTMLElement | null;
  armed: boolean;
  pinQueued: boolean;
  resizeObserver: ResizeObserver | null;
};

const state: GuardState = {
  thread: null,
  armed: true,
  pinQueued: false,
  resizeObserver: null,
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

function bindThread(thread: HTMLElement | null) {
  if (!thread || thread === state.thread) return;

  state.resizeObserver?.disconnect();
  state.thread = thread;

  thread.addEventListener('scroll', () => {
    state.armed = distanceFromEnd(thread) < LIVE_EDGE_THRESHOLD;
  }, { passive: true });

  state.resizeObserver = new ResizeObserver(() => {
    if (state.armed) queuePin();
  });
  state.resizeObserver.observe(thread);
}

function pinToLiveEdge() {
  const thread = findThread() ?? state.thread;
  bindThread(thread);
  if (!thread || !state.armed) return;
  thread.scrollTop = thread.scrollHeight;
}

function queuePin() {
  if (state.pinQueued) return;
  state.pinQueued = true;
  requestAnimationFrame(() => {
    state.pinQueued = false;
    pinToLiveEdge();
  });
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
      if (target?.closest(SEND_SELECTOR)) rearm();
    }, true);

    document.addEventListener('keydown', (event) => {
      const target = event.target as Element | null;
      if (event.key === 'Enter' && target?.matches(INPUT_SELECTOR)) rearm();
    }, true);

    bindThread(findThread());
    queuePin();
  };

  start();
}
