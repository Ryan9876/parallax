const assert = require('node:assert/strict');
const state = require('../.tmp-state/responseState.js');

let s = state.initialResponseState;
s = state.responseReducer(s, { type: 'START_THINKING' });
assert.equal(s.phase, 'THINKING');
assert.equal(state.motionForPhase(s.phase).laserActive, false);
s = state.responseReducer(s, { type: 'START_RESPONDING' });
assert.equal(s.phase, 'RESPONDING');
assert.equal(state.motionForPhase(s.phase).laserActive, true);
assert.equal(state.motionForPhase(s.phase).surfaceEnergy, 0.72);
s = state.responseReducer(s, { type: 'START_VERIFYING' });
assert.equal(s.phase, 'VERIFYING');
s = state.responseReducer(s, { type: 'COMPLETE' });
assert.equal(s.phase, 'COMPLETE');

let amendment = state.initialResponseState;
amendment = state.responseReducer(amendment, { type: 'START_THINKING' });
amendment = state.responseReducer(amendment, { type: 'REQUIRE_AMENDMENT' });
assert.equal(amendment.phase, 'SPEC_AMENDMENT');
assert.equal(state.motionForPhase(amendment.phase).laserActive, false);
assert.equal(state.motionForPhase(amendment.phase).surfaceEnergy, 0.22);
amendment = state.responseReducer(amendment, { type: 'START_THINKING' });
assert.equal(amendment.phase, 'THINKING');

const capacityMessage = 'Model capacity is temporarily unavailable. Your message is saved; when capacity returns, continue from here instead of sending it again.';
let capacity = state.initialResponseState;
capacity = state.responseReducer(capacity, { type: 'START_THINKING' });
capacity = state.responseReducer(capacity, { type: 'FAIL', error: capacityMessage });
assert.equal(capacity.phase, 'ERROR');
assert.equal(capacity.error, capacityMessage);
assert.match(capacity.error, /message is saved/);
assert.doesNotMatch(capacity.error, /protected scope/i);
assert.doesNotMatch(capacity.error, /retry or refine/i);
assert.equal(state.motionForPhase(capacity.phase).laserActive, false);

console.log('response state tests passed');
