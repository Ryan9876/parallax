const assert = require('node:assert/strict');
const {
  AUTONOMOUS_ENGINEERING_RUN_STATES,
  automaticAutonomyOperationKey,
  autonomyContinuationDisposition,
  canContinueEngineeringRunAutonomously,
  isAuthoritativeAutonomyAdvance,
  MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,
} = require('../.tmp-state/engineeringRunContinuation.js');

const base = {
  id: '44444444-4444-4444-8444-444444444444',
  revision: 7,
  binding_status: 'APPROVED_SPEC_BOUND',
};

for (const state of AUTONOMOUS_ENGINEERING_RUN_STATES) {
  assert.equal(
    canContinueEngineeringRunAutonomously({ ...base, state }),
    true,
    `${state} should be eligible for bounded autonomous continuation`,
  );
}

for (const state of ['SPECIFY', 'PAUSED', 'FAILED', 'REVIEW', 'SPEC_AMENDMENT', 'CANCELLED', 'COMPLETE']) {
  assert.equal(
    canContinueEngineeringRunAutonomously({ ...base, state }),
    false,
    `${state} must not auto-continue`,
  );
}

assert.equal(
  canContinueEngineeringRunAutonomously({ ...base, state: 'PLAN', binding_status: 'HISTORICAL_UNBOUND' }),
  false,
  'historical/unbound runs must never auto-continue',
);

const first = automaticAutonomyOperationKey({ ...base, state: 'PLAN' });
const second = automaticAutonomyOperationKey({ ...base, state: 'PLAN' });
assert.equal(first, second, 'automatic handoff identity must be deterministic for an exact run revision');
assert.equal(first, `autonomous-auto-${base.id}-${base.revision}`);
assert.ok(first.length <= 160, 'operation identity must stay within the protected API bound');
assert.throws(
  () => automaticAutonomyOperationKey({ ...base, id: '', state: 'PLAN' }),
  /id is required/,
);
assert.throws(
  () => automaticAutonomyOperationKey({ ...base, revision: -1, state: 'PLAN' }),
  /revision is invalid/,
);

assert.equal(MAX_AUTONOMY_REQUESTS_PER_CONTINUATION, 8);
assert.equal(
  isAuthoritativeAutonomyAdvance(
    { ...base, state: 'IMPLEMENT' },
    { ...base, revision: 8, state: 'BUILD' },
  ),
  true,
  'same-run newer revision is authoritative recovered progress',
);
assert.equal(
  isAuthoritativeAutonomyAdvance(
    { ...base, state: 'IMPLEMENT' },
    { ...base, revision: 7, state: 'IMPLEMENT' },
  ),
  false,
  'unchanged revision is not proof that an ambiguous request completed',
);
assert.equal(
  isAuthoritativeAutonomyAdvance(
    { ...base, state: 'IMPLEMENT' },
    { ...base, revision: 6, state: 'PLAN' },
  ),
  false,
  'older revision is never recovered progress',
);
assert.equal(
  isAuthoritativeAutonomyAdvance(
    { ...base, state: 'IMPLEMENT' },
    { ...base, id: '55555555-5555-4555-8555-555555555555', revision: 8, state: 'BUILD' },
  ),
  false,
  'a different run cannot reconcile an ambiguous request',
);
assert.equal(
  isAuthoritativeAutonomyAdvance({ ...base, state: 'IMPLEMENT' }, null),
  false,
  'missing canonical state is not proof of progress',
);
assert.equal(
  autonomyContinuationDisposition({ ...base, state: 'IMPLEMENT' }, 'MAX_STEPS_REACHED', 1),
  'CONTINUE',
);
assert.equal(
  autonomyContinuationDisposition(
    { ...base, state: 'VERIFY' },
    'MAX_STEPS_REACHED',
    MAX_AUTONOMY_REQUESTS_PER_CONTINUATION,
  ),
  'LIMIT_REACHED',
);
assert.equal(
  autonomyContinuationDisposition({ ...base, state: 'REVIEW' }, 'REVIEW_REQUIRED', 1),
  'STOP',
);
assert.equal(
  autonomyContinuationDisposition({ ...base, state: 'FAILED' }, 'MAX_STEPS_REACHED', 1),
  'STOP',
);
assert.throws(
  () => autonomyContinuationDisposition({ ...base, state: 'PLAN' }, 'MAX_STEPS_REACHED', 0),
  /request count is invalid/,
);

console.log('PASS engineering run continuation policy');
