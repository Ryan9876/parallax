const assert = require('node:assert/strict');
const { RunEventCursor } = require('../.tmp-state/runEventCursor.js');

const cursor = new RunEventCursor();
const runId = 'run-a';

assert.equal(cursor.last(runId), 0);
assert.equal(cursor.accept(runId, { id: 'event-1', run_id: runId, sequence: 1 }), true);
assert.equal(cursor.last(runId), 1);
assert.equal(cursor.accept(runId, { id: 'event-1-replayed', run_id: runId, sequence: 1 }), false);
assert.equal(cursor.accept(runId, { id: 'event-old', run_id: runId, sequence: 0 }), false);
assert.equal(cursor.accept(runId, { id: 'foreign', run_id: 'run-b', sequence: 2 }), false);
assert.equal(cursor.accept(runId, { id: 'event-3', run_id: runId, sequence: 3 }), true);
assert.equal(cursor.last(runId), 3);
assert.equal(cursor.accept(runId, { id: 'late-event-2', run_id: runId, sequence: 2 }), false);

cursor.reset(runId);
assert.equal(cursor.last(runId), 0);
assert.equal(cursor.accept(runId, { id: 'event-2-after-reset', run_id: runId, sequence: 2 }), true);

console.log('run-event cursor state tests passed');
