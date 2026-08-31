export const AUTONOMOUS_ENGINEERING_RUN_STATES = ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY'] as const;
export const MAX_AUTONOMY_REQUESTS_PER_CONTINUATION = 8;

const autonomousStates = new Set<string>(AUTONOMOUS_ENGINEERING_RUN_STATES);

export type EngineeringRunContinuationIdentity = {
  id: string;
  revision: number;
  state: string;
  binding_status: string;
};

export type AutonomyContinuationDisposition = 'CONTINUE' | 'STOP' | 'LIMIT_REACHED';

export function canContinueEngineeringRunAutonomously(run: EngineeringRunContinuationIdentity): boolean {
  return run.binding_status === 'APPROVED_SPEC_BOUND' && autonomousStates.has(run.state);
}

export function isAuthoritativeAutonomyAdvance(
  requested: EngineeringRunContinuationIdentity,
  latest: EngineeringRunContinuationIdentity | null | undefined,
): boolean {
  if (!latest || latest.id !== requested.id) return false;
  if (!Number.isInteger(requested.revision) || requested.revision < 0) return false;
  if (!Number.isInteger(latest.revision) || latest.revision < 0) return false;
  return latest.revision > requested.revision;
}

export function automaticAutonomyOperationKey(run: EngineeringRunContinuationIdentity): string {
  if (!run.id.trim()) throw new Error('Engineering Run id is required for automatic autonomy.');
  if (!Number.isInteger(run.revision) || run.revision < 0) throw new Error('Engineering Run revision is invalid for automatic autonomy.');
  const key = `autonomous-auto-${run.id}-${run.revision}`;
  if (key.length > 160) throw new Error('Automatic autonomy operation identity is unbounded.');
  return key;
}

export function autonomyContinuationDisposition(
  run: EngineeringRunContinuationIdentity,
  stopReason: string,
  completedRequests: number,
): AutonomyContinuationDisposition {
  if (!Number.isInteger(completedRequests) || completedRequests < 1) {
    throw new Error('Autonomy continuation request count is invalid.');
  }
  if (stopReason !== 'MAX_STEPS_REACHED' || !canContinueEngineeringRunAutonomously(run)) {
    return 'STOP';
  }
  return completedRequests >= MAX_AUTONOMY_REQUESTS_PER_CONTINUATION
    ? 'LIMIT_REACHED'
    : 'CONTINUE';
}
