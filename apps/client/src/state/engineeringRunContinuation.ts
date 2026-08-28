export const AUTONOMOUS_ENGINEERING_RUN_STATES = ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY'] as const;

const autonomousStates = new Set<string>(AUTONOMOUS_ENGINEERING_RUN_STATES);

export type EngineeringRunContinuationIdentity = {
  id: string;
  revision: number;
  state: string;
  binding_status: string;
};

export function canContinueEngineeringRunAutonomously(run: EngineeringRunContinuationIdentity): boolean {
  return run.binding_status === 'APPROVED_SPEC_BOUND' && autonomousStates.has(run.state);
}

export function automaticAutonomyOperationKey(run: EngineeringRunContinuationIdentity): string {
  if (!run.id.trim()) throw new Error('Engineering Run id is required for automatic autonomy.');
  if (!Number.isInteger(run.revision) || run.revision < 0) throw new Error('Engineering Run revision is invalid for automatic autonomy.');
  const key = `autonomous-auto-${run.id}-${run.revision}`;
  if (key.length > 160) throw new Error('Automatic autonomy operation identity is unbounded.');
  return key;
}
