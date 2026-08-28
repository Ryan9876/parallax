import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, '../src/App.tsx'), 'utf8');

function assert(condition, message) {
  if (!condition) throw new Error(`w8-s3 plain-language contract: ${message}`);
}

const forbiddenPrimaryCopy = [
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

for (const phrase of forbiddenPrimaryCopy) {
  assert(!source.includes(phrase), `ordinary root shell still exposes legacy phrase: ${phrase}`);
}

const requiredPrimaryCopy = [
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

for (const phrase of requiredPrimaryCopy) {
  assert(source.includes(phrase), `required plain-language phrase is missing: ${phrase}`);
}

assert(/amendmentAction:\s*\{[^}]*minHeight:\s*44/.test(source), 'scope-change actions must remain at least 44px high');
assert(/emptyCopy:\s*\{[^}]*fontSize:\s*16/.test(source), 'ordinary empty-state body copy must remain at least 16px');
assert(/meta:\s*\{[^}]*fontSize:\s*12/.test(source), 'ordinary secondary status text must remain at least 12px');
assert(source.includes("mode === 'reason' ? 'ASK' : 'BUILD'"), 'ordinary mode labels must remain Ask/Build');
assert(source.includes("message.id === activePrintId ? 'RESPONDING' : 'READY'"), 'ordinary response status must remain Responding/Ready');

console.log('PASS: W8-S3 root shell defaults to plain language, keeps error detail secondary, and preserves readable action/status minimums.');
