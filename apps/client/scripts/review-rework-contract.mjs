import { readFileSync } from 'node:fs';

function source(path) { return readFileSync(new URL(`../${path}`, import.meta.url), 'utf8'); }
function assert(condition, message) { if (!condition) throw new Error(message); }

const api = source('src/lib/api.ts');
const hook = source('src/hooks/useEngineeringRun.ts');
const panel = source('src/components/ReviewReworkPanel.tsx');
const desktop = source('src/components/EngineeringRunStatus.tsx');
const mobile = source('src/components/mobile/MobileExperience.tsx');
const app = source('src/App.tsx');
const fallback = source('src/FallbackApp.tsx');

assert(api.includes('/review-rework'), 'review rework API endpoint is not wired');
assert(api.includes('expected_revision: run.revision'), 'review rework API must remain revision-bound');
assert(hook.includes('requestReviewRework'), 'engineering hook lacks explicit REVIEW rework action');
assert(hook.includes('reviewed.revision') && hook.includes('latestEngineeringRun'), 'split-boundary reconciliation is missing');
assert(panel.includes('accessibilityRole="checkbox"'), 'acceptance selection is not accessibility-observable');
assert(panel.includes('accessibilityLabel="What should Parallax change"'), 'correction input lacks accessible identity');
assert(panel.includes('Request changes'), 'explicit human correction action is missing');
assert(panel.includes('maxLength={1200}'), 'client finding bound drifted from API contract');
assert(desktop.includes('<ReviewReworkPanel'), 'desktop REVIEW does not expose correction UI');
assert(mobile.includes('<ReviewReworkPanel'), 'compact mobile REVIEW does not expose correction UI');
assert(app.match(/onRequestChanges=/g)?.length === 2, 'main app must wire desktop and mobile rework actions');
assert(fallback.includes('onRequestChanges='), 'reduced-graphics client must preserve REVIEW rework');
console.log(JSON.stringify({ reviewRework: true, desktop: true, mobile: true, reducedGraphics: true, revisionBound: true }));
