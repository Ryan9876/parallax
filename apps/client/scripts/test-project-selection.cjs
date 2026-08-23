const assert = require('node:assert/strict');
const selection = require('../.tmp-state/projectSelection.js');

const alpha = { id: '11111111-1111-4111-8111-111111111111' };
const beta = { id: '22222222-2222-4222-8222-222222222222' };

assert.equal(selection.hasProject([alpha], alpha.id), true);
assert.equal(selection.hasProject([alpha], beta.id), false);
assert.equal(selection.hasProject([alpha], null), false);

assert.equal(
  selection.reconcileProjectSelection([alpha, beta], beta.id, alpha.id),
  alpha.id,
  'a valid active/preferred Project should win deterministically',
);
assert.equal(
  selection.reconcileProjectSelection([alpha, beta], beta.id),
  beta.id,
  'a valid explicit selection should be retained',
);
assert.equal(
  selection.reconcileProjectSelection([alpha], beta.id),
  alpha.id,
  'exactly one owner-scoped Project may auto-select',
);
assert.equal(
  selection.reconcileProjectSelection([alpha], beta.id, null, false),
  null,
  'historical/unbound compatibility may suppress sole-Project inference',
);
assert.equal(
  selection.reconcileProjectSelection([alpha, beta], 'stale-project'),
  null,
  'stale selections must clear when more than one valid Project exists',
);
assert.equal(
  selection.requireCanonicalCodeProject([alpha, beta], alpha.id),
  alpha.id,
  'Code creation may use only an ID present in the owner-scoped Project list',
);
assert.equal(
  selection.requireCanonicalCodeProject([alpha, beta], 'caller-invented'),
  null,
  'invented Project identity must fail closed',
);

const updated = selection.upsertProject([alpha], { id: alpha.id, marker: 'server' });
assert.equal(updated.length, 1);
assert.equal(updated[0].marker, 'server');
assert.deepEqual(
  selection.upsertProject([alpha], { id: beta.id }).map((project) => project.id),
  [beta.id, alpha.id],
  'server-returned created Project should be inserted without synthetic IDs',
);

console.log('project selection state tests passed');
