type AuthenticationRequiredListener = () => void;

let authenticationRequiredListener: AuthenticationRequiredListener | null = null;

export function installAuthenticationRequiredListener(listener: AuthenticationRequiredListener): () => void {
  authenticationRequiredListener = listener;
  return () => {
    if (authenticationRequiredListener === listener) authenticationRequiredListener = null;
  };
}

export function emitAuthenticationRequired(): void {
  authenticationRequiredListener?.();
}
