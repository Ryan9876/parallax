import type { EngineeringRunDto, ResponsePhase, WorkSpecificationDto } from './api';

export type WorkflowGuidanceKind =
  | 'ask-ready'
  | 'describe-goal'
  | 'create-plan'
  | 'review-plan'
  | 'approved-plan'
  | 'active'
  | 'failed'
  | 'paused'
  | 'cancelled'
  | 'review'
  | 'complete'
  | 'amendment';

export type WorkflowActionIntent =
  | 'create-plan'
  | 'review-plan'
  | 'view-progress'
  | 'continue-work'
  | 'open-activity'
  | 'continue-approved'
  | 'start-new-goal'
  | null;

export type WorkflowGuidanceTone = 'neutral' | 'active' | 'attention' | 'ready' | 'complete';

export type WorkflowGuidance = {
  kind: WorkflowGuidanceKind;
  eyebrow: string;
  title: string;
  description: string;
  actionIntent: WorkflowActionIntent;
  actionLabel: string | null;
  tone: WorkflowGuidanceTone;
};

export type WorkflowGuidanceInput = {
  mode: 'reason' | 'code';
  phase?: ResponsePhase | string | null;
  conversationStatus?: string | null;
  specification?: WorkSpecificationDto | null;
  run?: EngineeringRunDto | null;
  canDraft?: boolean;
  hasApprovedSpecification?: boolean;
  runError?: string | null;
};

function guidance(
  kind: WorkflowGuidanceKind,
  eyebrow: string,
  title: string,
  description: string,
  tone: WorkflowGuidanceTone,
  actionIntent: WorkflowActionIntent = null,
  actionLabel: string | null = null,
): WorkflowGuidance {
  return { kind, eyebrow, title, description, actionIntent, actionLabel, tone };
}

function activeRunGuidance(state: string): WorkflowGuidance {
  if (state === 'PLAN' || state === 'SPECIFY') {
    return guidance(
      'active',
      'RIGHT NOW',
      'Planning the work',
      'Parallax is turning the approved plan into the protected steps needed to make the change.',
      'active',
      'view-progress',
      'View progress',
    );
  }
  if (state === 'IMPLEMENT' || state === 'BUILD') {
    return guidance(
      'active',
      'RIGHT NOW',
      'Making the changes',
      'Parallax is working through the approved changes. You do not need to do anything right now.',
      'active',
      'view-progress',
      'View progress',
    );
  }
  if (state === 'TEST' || state === 'VERIFY') {
    return guidance(
      'active',
      'RIGHT NOW',
      'Checking the result',
      'Parallax is checking the protected result against the approved plan before asking you to review it.',
      'active',
      'view-progress',
      'View progress',
    );
  }
  return guidance(
    'active',
    'RIGHT NOW',
    'Working on your request',
    'Parallax is continuing the protected work from the plan you approved.',
    'active',
    'view-progress',
    'View progress',
  );
}

/**
 * Pure presentation mapping over canonical state already owned by the server.
 * This function never performs I/O, persists lifecycle state, or grants action authority.
 */
export function getWorkflowGuidance(input: WorkflowGuidanceInput): WorkflowGuidance {
  const specification = input.specification ?? null;
  const run = input.run ?? null;
  const amendment = input.phase === 'SPEC_AMENDMENT' || input.conversationStatus === 'SPEC_AMENDMENT';

  if (input.mode === 'code' && amendment) {
    return guidance(
      'amendment',
      'NEEDS YOUR CHOICE',
      'Your request changed',
      'The newer request is different from the plan you approved. Parallax stopped before changing that approved work.',
      'attention',
      input.hasApprovedSpecification ? 'continue-approved' : 'start-new-goal',
      input.hasApprovedSpecification ? 'Continue approved work' : 'Start as a new goal',
    );
  }

  if (input.mode === 'code' && (input.runError || run?.state === 'FAILED')) {
    return guidance(
      'failed',
      'NEEDS ATTENTION',
      'Something needs attention',
      'Your saved work is still here. Continue the same work when you are ready, and Parallax will retry from the server-owned checkpoint.',
      'attention',
      'continue-work',
      'Try again',
    );
  }

  if (input.mode === 'code' && run?.state === 'PAUSED') {
    return guidance(
      'paused',
      'PAUSED',
      'Work is paused',
      'Nothing is being changed while this work is paused. Continue when you are ready.',
      'neutral',
      'continue-work',
      'Continue work',
    );
  }

  if (input.mode === 'code' && run?.state === 'CANCELLED') {
    return guidance(
      'cancelled',
      'STOPPED',
      'Work was stopped',
      'This protected run is no longer continuing. Start a new goal if you want Parallax to do different work.',
      'neutral',
    );
  }

  if (input.mode === 'code' && run?.state === 'REVIEW') {
    return guidance(
      'review',
      'READY FOR YOU',
      'Ready for your review',
      'Parallax finished the protected work and is waiting for your review. This does not mean the result was merged or deployed.',
      'ready',
      'open-activity',
      'Review result',
    );
  }

  if (input.mode === 'code' && run?.state === 'COMPLETE') {
    return guidance(
      'complete',
      'DONE',
      'Protected work is complete',
      'The protected run is complete. Production delivery is a separate action and is not implied by this status.',
      'complete',
      'view-progress',
      'View progress',
    );
  }

  if (input.mode === 'code' && run) return activeRunGuidance(run.state);

  if (input.mode === 'code' && specification?.status === 'APPROVED') {
    return guidance(
      'approved-plan',
      'RIGHT NOW',
      'Starting approved work',
      'Your build plan is approved. Parallax is preparing the protected work from that approved plan.',
      'active',
      'view-progress',
      'View progress',
    );
  }

  if (input.mode === 'code' && specification?.status === 'DRAFT') {
    return guidance(
      'review-plan',
      'NEXT STEP',
      'Review your build plan',
      'Check the plan below, then approve it only when it matches what you want Parallax to build.',
      'ready',
      'review-plan',
      'Review build plan',
    );
  }

  if (input.mode === 'code' && input.canDraft) {
    return guidance(
      'create-plan',
      'NEXT STEP',
      'Create your build plan',
      'Turn this request into a clear plan before Parallax begins making changes.',
      'ready',
      'create-plan',
      'Create build plan',
    );
  }

  if (input.mode === 'code') {
    return guidance(
      'describe-goal',
      'START HERE',
      'Describe the outcome you want',
      'Tell Parallax what should change, what success looks like, and any important limits.',
      'neutral',
    );
  }

  return guidance(
    'ask-ready',
    'READY',
    'Ask anything',
    'Ask a question, explore an idea, or switch to Build when you want Parallax to make a governed change.',
    'neutral',
  );
}
