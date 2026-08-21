type ApprovedWorkSpecificationEvent = {
  conversationId: string;
  specificationId: string;
};

type Listener = (event: ApprovedWorkSpecificationEvent) => void;

const listeners = new Set<Listener>();

export function publishApprovedWorkSpecification(event: ApprovedWorkSpecificationEvent) {
  for (const listener of listeners) listener(event);
}

export function subscribeApprovedWorkSpecification(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
