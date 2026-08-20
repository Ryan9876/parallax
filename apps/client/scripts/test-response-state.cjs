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
console.log('response state tests passed');
