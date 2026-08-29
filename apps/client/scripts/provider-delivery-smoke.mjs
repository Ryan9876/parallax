import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../src/components/EngineeringRunStatus.tsx', import.meta.url), 'utf8');

assert.match(source, /const DELIVERY_MUTABLE_STAGES = \['SPECIFY', 'PLAN'\]/);
assert.match(source, /\/v1\/projects\/\$\{projectId\}\/delivery/);
assert.match(source, /delivery_mode: deliveryMode/);
assert.match(source, /'source-only'/);
assert.match(source, /'vercel-preview'/);
assert.match(source, /Download source/);
assert.match(source, /Vercel Preview/);
assert.match(source, /IIS · local · other/);
assert.match(source, /\/source-download/);
assert.match(source, /run\.state === 'REVIEW'/);
assert.match(source, /Platform\.OS === 'web'/);
assert.match(source, /Download verified source/);
assert.match(source, /Open this project on web or desktop/);

console.log('PASS: provider-independent delivery controls stay bounded to pre-implementation selection and REVIEW source handoff.');
