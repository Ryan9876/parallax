export type ResponsePhase =
  | 'IDLE'
  | 'THINKING'
  | 'RESPONDING'
  | 'VERIFYING'
  | 'COMPLETE'
  | 'SPEC_AMENDMENT'
  | 'ERROR';

export type ResponseState = {
  phase: ResponsePhase;
  error?: string;
};

export type ResponseEvent =
  | { type: 'RESET' }
  | { type: 'START_THINKING' }
  | { type: 'START_RESPONDING' }
  | { type: 'START_VERIFYING' }
  | { type: 'COMPLETE' }
  | { type: 'REQUIRE_AMENDMENT' }
  | { type: 'FAIL'; error: string };

export const initialResponseState: ResponseState = { phase: 'IDLE' };

const allowed: Record<ResponsePhase, readonly ResponsePhase[]> = {
  IDLE: ['THINKING'],
  THINKING: ['RESPONDING', 'SPEC_AMENDMENT', 'ERROR'],
  RESPONDING: ['VERIFYING', 'SPEC_AMENDMENT', 'ERROR'],
  VERIFYING: ['COMPLETE', 'SPEC_AMENDMENT', 'ERROR'],
  COMPLETE: ['IDLE', 'THINKING'],
  SPEC_AMENDMENT: ['IDLE', 'THINKING'],
  ERROR: ['IDLE', 'THINKING'],
};

function transition(state: ResponseState, phase: ResponsePhase, error?: string): ResponseState {
  if (!allowed[state.phase].includes(phase)) {
    throw new Error(`Invalid response transition ${state.phase} -> ${phase}`);
  }
  return error ? { phase, error } : { phase };
}

export function responseReducer(state: ResponseState, event: ResponseEvent): ResponseState {
  switch (event.type) {
    case 'RESET':
      return state.phase === 'IDLE' ? state : transition(state, 'IDLE');
    case 'START_THINKING':
      return transition(state, 'THINKING');
    case 'START_RESPONDING':
      return transition(state, 'RESPONDING');
    case 'START_VERIFYING':
      return transition(state, 'VERIFYING');
    case 'COMPLETE':
      return transition(state, 'COMPLETE');
    case 'REQUIRE_AMENDMENT':
      return transition(state, 'SPEC_AMENDMENT');
    case 'FAIL':
      return transition(state, 'ERROR', event.error);
  }
}

export type MotionState = {
  surfaceEnergy: number;
  laserActive: boolean;
};

export function motionForPhase(phase: ResponsePhase): MotionState {
  switch (phase) {
    case 'IDLE':
    case 'COMPLETE':
      return { surfaceEnergy: 0.18, laserActive: false };
    case 'THINKING':
      return { surfaceEnergy: 0.42, laserActive: false };
    case 'RESPONDING':
      return { surfaceEnergy: 0.72, laserActive: true };
    case 'VERIFYING':
      return { surfaceEnergy: 0.48, laserActive: false };
    case 'SPEC_AMENDMENT':
      return { surfaceEnergy: 0.22, laserActive: false };
    case 'ERROR':
      return { surfaceEnergy: 0.12, laserActive: false };
  }
}
