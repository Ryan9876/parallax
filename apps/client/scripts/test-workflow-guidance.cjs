const assert = require('node:assert/strict');
const { getWorkflowGuidance } = require('../.tmp-guidance/workflowGuidance.js');

function specification(status = 'DRAFT') {
  return {
    id: 'spec-secret-id',
    conversation_id: 'conversation-secret-id',
    revision: 3,
    status,
    title: 'Build something useful',
    objective: 'Create the requested experience',
    constraints: [],
    acceptance_criteria: ['Works as requested'],
    risks: [],
    open_questions: [],
    confidence: 0.95,
    program_version: 'internal-program',
    model_id: 'provider-secret-name',
    created_at: '2026-08-29T00:00:00Z',
    updated_at: '2026-08-29T00:00:00Z',
    approved_at: status === 'APPROVED' ? '2026-08-29T00:00:00Z' : null,
  };
}

function run(state, resume_stage = null) {
  return {
    id: 'run-secret-id',
    conversation_id: 'conversation-secret-id',
    spec_id: 'spec-secret-id',
    project_id: 'project-secret-id',
    project_binding_status: 'PROJECT_BOUND',
    work_specification_id: 'work-spec-secret-id',
    work_specification_revision: 3,
    work_specification_digest: 'digest-secret',
    binding_status: 'APPROVED_SPEC_BOUND',
    acceptance_criteria: [],
    state,
    resume_stage,
    revision: 9,
    workspace_ref: 'workspace-secret',
    last_failure_code: state === 'FAILED' ? 'SECRET_FAILURE_CODE' : null,
    completed_at: state === 'COMPLETE' ? '2026-08-29T00:00:00Z' : null,
    created_at: '2026-08-29T00:00:00Z',
    updated_at: '2026-08-29T00:00:00Z',
    attempts: [],
  };
}

function map(input) {
  return getWorkflowGuidance({ mode: 'code', ...input });
}

function assertGuidance(input, expectedKind, expectedTitle, expectedAction) {
  const result = map(input);
  assert.equal(result.kind, expectedKind);
  assert.equal(result.title, expectedTitle);
  assert.equal(result.actionIntent, expectedAction);
  assert.ok(result.eyebrow.length > 0);
  assert.ok(result.description.length > 0);
  const ordinary = `${result.eyebrow} ${result.title} ${result.description} ${result.actionLabel ?? ''}`;
  for (const forbidden of [
    'spec-secret-id',
    'run-secret-id',
    'project-secret-id',
    'provider-secret-name',
    'SECRET_FAILURE_CODE',
  ]) assert.equal(ordinary.includes(forbidden), false, `ordinary guidance leaked ${forbidden}`);
  for (const rawStage of ['IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'FAILED', 'PAUSED', 'CANCELLED']) {
    assert.equal(ordinary.includes(rawStage), false, `ordinary guidance leaked raw stage ${rawStage}`);
  }
  return result;
}

assert.equal(getWorkflowGuidance({ mode: 'reason' }).kind, 'ask-ready');
assertGuidance({}, 'describe-goal', 'Describe the outcome you want', null);
assertGuidance({ canDraft: true }, 'create-plan', 'Create your build plan', 'create-plan');
assertGuidance({ specification: specification('DRAFT') }, 'review-plan', 'Review your build plan', 'review-plan');
assertGuidance({ specification: specification('APPROVED') }, 'approved-plan', 'Starting approved work', 'view-progress');
assertGuidance({ specification: specification('APPROVED'), run: run('PLAN') }, 'active', 'Planning the work', 'view-progress');
assertGuidance({ specification: specification('APPROVED'), run: run('IMPLEMENT') }, 'active', 'Making the changes', 'view-progress');
assertGuidance({ specification: specification('APPROVED'), run: run('TEST') }, 'active', 'Checking the result', 'view-progress');
assertGuidance({ specification: specification('APPROVED'), run: run('FAILED', 'BUILD') }, 'failed', 'Something needs attention', 'continue-work');
assertGuidance({ specification: specification('APPROVED'), run: run('PAUSED', 'VERIFY') }, 'paused', 'Work is paused', 'continue-work');
assertGuidance({ specification: specification('APPROVED'), run: run('CANCELLED', 'BUILD') }, 'cancelled', 'Work was stopped', null);
const review = assertGuidance({ specification: specification('APPROVED'), run: run('REVIEW') }, 'review', 'Ready for your review', 'open-activity');
assert.match(review.description, /does not mean/i);
assertGuidance({ specification: specification('APPROVED'), run: run('COMPLETE') }, 'complete', 'Protected work is complete', 'view-progress');

// A status-fetch failure without an authoritative run must fail closed and must not expose a no-op resume action.
assertGuidance({
  specification: specification('APPROVED'),
  runError: 'status endpoint unavailable',
}, 'failed', 'Progress is temporarily unavailable', null);

// Consequential canonical states take precedence over generic active/plan state.
assertGuidance({
  phase: 'SPEC_AMENDMENT',
  conversationStatus: 'SPEC_AMENDMENT',
  specification: specification('APPROVED'),
  run: run('FAILED', 'BUILD'),
  runError: 'internal transport detail',
  hasApprovedSpecification: true,
}, 'amendment', 'Your request changed', 'continue-approved');

assertGuidance({
  specification: specification('APPROVED'),
  run: run('PAUSED', 'TEST'),
  runError: 'temporary request failure',
}, 'failed', 'Something needs attention', 'continue-work');

// Resume stage may affect server continuation but must never masquerade as current ordinary state.
const paused = map({ specification: specification('APPROVED'), run: run('PAUSED', 'IMPLEMENT') });
assert.equal(paused.title, 'Work is paused');
assert.equal(`${paused.title} ${paused.description}`.includes('Making the changes'), false);

console.log('PASS: W8-S4 deterministic workflow guidance contract');
