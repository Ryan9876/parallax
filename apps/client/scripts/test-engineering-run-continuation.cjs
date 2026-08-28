const assert = require('node:assert/strict');
const {
  AUTONOMOUS_ENGINEERING_RUN_STATES,
  automaticAutonomyOperationKey,
  canContinueEngineeringRunAutonomously,
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

console.log('PASS engineering run continuation policy');
