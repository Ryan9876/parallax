const assert = require('node:assert/strict');
const {
  WORK_SPEC_RATE_LIMIT_MESSAGE,
  workSpecificationDraftFailureMessage,
} = require('../.tmp-state/workSpecificationState.js');

assert.equal(
  workSpecificationDraftFailureMessage(429, 'provider raw message must not be shown'),
  WORK_SPEC_RATE_LIMIT_MESSAGE,
);
assert.match(WORK_SPEC_RATE_LIMIT_MESSAGE, /Retry Capture Spec later/);
assert.match(WORK_SPEC_RATE_LIMIT_MESSAGE, /objective is preserved/);
assert.equal(
  workSpecificationDraftFailureMessage(503, 'The Work Specification model provider is temporarily unavailable.'),
  'The Work Specification model provider is temporarily unavailable.',
);
assert.equal(
  workSpecificationDraftFailureMessage(null, ''),
  'Specification drafting failed. Your objective is preserved; retry Capture Spec.',
);

console.log('work specification state tests passed');
