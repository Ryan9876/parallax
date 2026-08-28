import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const read = (path) => readFileSync(join(here, path), 'utf8');
const app = read('../src/App.tsx');
const header = read('../src/components/EditorialWorkspaceHeader.tsx');
const progress = read('../src/components/EngineeringRunStatus.tsx');
const mobile = read('../src/components/mobile/MobileExperience.tsx');

function assert(condition, message) {
  if (!condition) throw new Error(`w8-s3 plain-language contract: ${message}`);
}

const forbiddenRootCopy = [
  'approved specification, engineering evidence, and protected execution path',
  'protected build flow',
  'Resolving the active objective',
  'Verifying response',
  'Specification amendment required',
  'Start new objective',
  'Engineering workspace',
  'Reasoning workspace',
  'canonical Project identity visible',
  "mode === 'reason' ? 'REASON' : 'CODE'",
  "message.id === activePrintId ? 'LIVE' : 'COMPLETE'",
  'state.error ??',
];

for (const phrase of forbiddenRootCopy) {
  assert(!app.includes(phrase), `ordinary root shell still exposes legacy phrase: ${phrase}`);
}

const requiredRootCopy = [
  'Parallax keeps your request, approved plan, saved work, and review steps aligned while you build.',
  'Working through your request…',
  'Checking the response…',
  'Your request changed',
  'Continue approved work',
  'Start a new goal',
  'Build workspace',
  'Ask workspace',
  'Parallax couldn’t finish that response. Your conversation is saved. Try again.',
];

for (const phrase of requiredRootCopy) {
  assert(app.includes(phrase), `required plain-language phrase is missing: ${phrase}`);
}

assert(/amendmentAction:\s*\{[^}]*minHeight:\s*44/.test(app), 'scope-change actions must remain at least 44px high');
assert(/emptyCopy:\s*\{[^}]*fontSize:\s*16/.test(app), 'ordinary empty-state body copy must remain at least 16px');
assert(/meta:\s*\{[^}]*fontSize:\s*12/.test(app), 'ordinary secondary status text must remain at least 12px');
assert(app.includes("mode === 'reason' ? 'ASK' : 'BUILD'"), 'ordinary mode labels must remain Ask/Build');
assert(app.includes("message.id === activePrintId ? 'RESPONDING' : 'READY'"), 'ordinary response status must remain Responding/Ready');

assert(!header.includes('Project · ${projectId}'), 'desktop header must not expose a Project ID');
assert(!header.includes('projectId.slice'), 'desktop header must not shorten a Project ID into ordinary copy');
assert(header.includes("return 'Project selected';"), 'desktop header must use a plain Project-selection label');
assert(header.includes("const label = item === 'reason' ? 'Ask' : 'Build';"), 'desktop header must render Ask/Build rather than internal mode names');
assert(/modeButton:\s*\{[^}]*minHeight:\s*44/.test(header), 'desktop Ask/Build controls must remain at least 44px high');
assert(/subtitle:\s*\{[^}]*fontSize:\s*15/.test(header), 'desktop header subtitle must remain readable');

const forbiddenProgressCopy = [
  'protected build environment',
  'Older run · view only',
  'finished the build flow',
  'This older run is preserved',
];
for (const phrase of forbiddenProgressCopy) {
  assert(!progress.includes(phrase), `ordinary progress surface still exposes legacy phrase: ${phrase}`);
}
assert(progress.includes('Older work · view only'), 'ordinary progress surface must use plain historical-work language');
assert(progress.includes('Parallax finished the work and the result is ready.'), 'ordinary progress completion copy must stay outcome-oriented');
assert(progress.includes('System object: Engineering Run'), 'Engineering Run identity must remain available in technical details');
assert(progress.includes('Work Specification revision:'), 'Work Specification revision must remain available in technical details');

assert(!mobile.includes('Project ${projectId.slice'), 'mobile ordinary surfaces must not expose shortened Project IDs');
assert(mobile.includes("return 'Project selected';"), 'mobile Project fallback must use a plain selection label');
assert(/modeButton:\s*\{[^}]*minHeight:\s*44/.test(mobile), 'mobile Ask/Build controls must remain at least 44px high');
assert(mobile.includes('Parallax finished the work and the result is ready.'), 'mobile completion copy must stay outcome-oriented');
assert(mobile.includes('Project ID:'), 'raw Project identity must remain available in mobile technical details');
assert(mobile.includes('Binding status:'), 'raw binding status must remain available in mobile technical details');

console.log('PASS: W8-S3 ordinary shell, headers, mobile context, and progress surfaces default to plain language while technical detail remains available on demand.');
