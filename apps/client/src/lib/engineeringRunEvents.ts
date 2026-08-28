type EngineeringRunFailure = {
  conversationId: string;
  runId: string;
  message: string;
};

type FailureListener = () => void;
type RetryListener = (conversationId: string) => void;

const failures = new Map<string, EngineeringRunFailure>();
const failureListeners = new Set<FailureListener>();
const retryListeners = new Set<RetryListener>();

function notifyFailures() {
  for (const listener of failureListeners) listener();
}

export function publishEngineeringRunFailure(event: EngineeringRunFailure) {
  failures.set(event.conversationId, event);
  notifyFailures();
}

export function clearEngineeringRunFailure(conversationId: string | null) {
  if (!conversationId || !failures.delete(conversationId)) return;
  notifyFailures();
}

export function getEngineeringRunFailure(conversationId: string | null): EngineeringRunFailure | null {
  if (!conversationId) return null;
  return failures.get(conversationId) ?? null;
}

export function subscribeEngineeringRunFailures(listener: FailureListener) {
  failureListeners.add(listener);
  return () => {
    failureListeners.delete(listener);
  };
}

export function requestEngineeringRunRetry(conversationId: string) {
  for (const listener of retryListeners) listener(conversationId);
}

export function subscribeEngineeringRunRetry(listener: RetryListener) {
  retryListeners.add(listener);
  return () => {
    retryListeners.delete(listener);
  };
}
