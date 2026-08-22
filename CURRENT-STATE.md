# Parallax 2.0 Current State

Version: 0.13.4 production
Date: 2026-08-22
Status: DEPLOYMENT-VERIFIED — FIRST REAL OPERATOR SANDBOX EXECUTION STILL PENDING
Production branch: `main`
Production application commit: `1b09c0c399f56b3c66efa8b6be3d6f9ba246f463`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_DkmFZx92i6dJkKGJTfgRqgBjrwMd`
Production API deployment: `dpl_G5hz69cCs877NE2kkuPGLMweaHuK`

## Current production baseline

Parallax 2.0 v0.13.4 is merged to `main` and deployment-verified on both production Vercel projects. The current baseline combines the v0.13 bounded-autonomy pilot, the v0.13.1 active-spec production guard, the v0.13.2 visual integration, the v0.13.3 amendment-approval lifecycle repair, and the v0.13.4 explicit approved-scope recovery path.

The production Code path includes:

- persistent Work Specifications with explicit operator approval;
- immutable approved-spec binding for Engineering Runs;
- bounded autonomous PLAN / BUILD / TEST / VERIFY coordination;
- isolated Vercel Sandbox execution for registered protected commands;
- fail-closed execution when the isolated executor is unavailable;
- server-owned acceptance criteria, stage transitions, command registry, and stop reasons;
- a `Run autonomously` control on eligible bound Engineering Run stages;
- explicit stops at IMPLEMENT when real implementation evidence is required and at REVIEW when independent review authority is required;
- amendment handling that keeps material scope changes fail-closed until operator authority is re-established.

The pilot still does **not** grant autonomous source editing, arbitrary shell access, Work Specification self-approval, Git commit/push/merge, or autonomous production deployment authority.

## v0.13.2 visual integration — live

The production workspace now uses the approved Parallax visual language rather than the older aperture identity and effectively static field:

- transparent glossy 3D interlocking-knot identity in primary and assistant-avatar use;
- perceptibly animated Ambient Chroma Flow / living surface during normal 5–15 second observation;
- updated rounded translucent Work Specification material;
- compact stream-synchronized optical engraving treatment for active assistant responses;
- response-follow behavior that keeps live output visible while respecting intentional upward scrolling;
- composer-height clearance so active content is not hidden behind the input surface;
- mobile geometry and controls validated without horizontal overflow.

The durable knot, ambient-motion, Work Specification material, and optical-typesetter rules are recorded in `DESIGN-SYSTEM.md`.

## v0.13.3 amendment approval lifecycle — live

A material scope change correctly moves a conversation to `SPEC_AMENDMENT`. v0.13.3 repaired the future approval path so that approving the **current replacement DRAFT** returns that conversation to `ACTIVE` only after the specification approval succeeds.

The guard is deliberately narrow:

- the conversation must already be `SPEC_AMENDMENT`;
- the specification being approved must still be a `DRAFT`;
- it must be the latest Work Specification for that conversation;
- re-approving an older already-approved specification cannot bypass a newer amendment stop.

No database migration was required.

## v0.13.4 explicit approved-scope recovery — live

Pre-v0.13.3 conversations can legitimately exist in an ambiguous persisted shape: `SPEC_AMENDMENT` while the latest Work Specification is already `APPROVED`. That state cannot be safely auto-repaired because it can mean either a legacy stuck replacement approval or an operator who triggered an amendment but now wants to return to the prior approved scope.

v0.13.4 therefore adds explicit human recovery instead of timestamp inference or silent migration:

- the shared Work Specification surface detects `SPEC_AMENDMENT` + latest `APPROVED` and offers `RESUME SCOPE`;
- the production API exposes `POST /v1/conversations/{conversation_id}/work-specifications/resume-approved-scope`;
- the server permits the transition only when the conversation is currently `SPEC_AMENDMENT` and its latest Work Specification is `APPROVED`;
- if the latest Work Specification is a `DRAFT`, recovery is rejected and the operator must use the normal approval path;
- success changes only the conversation status to `ACTIVE`; it does not create, approve, supersede, or rewrite a Work Specification;
- the web workspace reloads after successful recovery so the client presents the authoritative server state;
- compact controls wrap on narrow layouts rather than overlapping.

No database migration was required.

## Validation evidence

PR `#25`, head `eb6f6d90d2b0a1755a360e8d0994233fbfd44b0b`, passed both protected workflows before merge:

- `Parallax P2 CI` run `32586806925` — SUCCESS;
- `Bounded Autonomy Pilot` run `32586806956` — SUCCESS.

The passing release gate covered:

- specification validation;
- full API regression tests, including deterministic amendment-resume safety cases;
- client typecheck;
- response-state tests;
- web export;
- browser / Skia acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy release compilation;
- bounded-autonomy regressions and authority boundaries.

PR `#25` was squash-merged to `main` as `1b09c0c399f56b3c66efa8b6be3d6f9ba246f463`.

The visual integration introduced in v0.13.2 was separately validated before promotion, including mobile, tablet, and desktop browser evidence that the approved knot rendered and animated frames changed over time.

## Deployment verification

### Web

Production deployment `dpl_DkmFZx92i6dJkKGJTfgRqgBjrwMd` is READY, targets production, and carries main commit `1b09c0c399f56b3c66efa8b6be3d6f9ba246f463`.

Its aliases include:

- `parallax-ashy-one-20.vercel.app`;
- `parallax-lew7.vercel.app`;
- `parallax-git-main-lew7.vercel.app`.

A direct request to `https://parallax-ashy-one-20.vercel.app/` returned HTTP 200 after the deployment and served the current web bundle.

### API

Production deployment `dpl_G5hz69cCs877NE2kkuPGLMweaHuK` is READY, targets production, and carries the same main commit.

Its aliases include:

- `parallax-api-tan.vercel.app`;
- `parallax-api-lew7.vercel.app`;
- `parallax-api-git-main-lew7.vercel.app`.

A direct request to `https://parallax-api-tan.vercel.app/openapi.json` returned HTTP 200 after deployment and advertises the new `resume-approved-scope` endpoint. An unauthenticated request to `/v1/conversations` returns HTTP 401, confirming that private production authentication remains enforced.

## Remaining operator verification

The current web and API releases are deployed and automated validation is complete. The first real user-driven isolated Sandbox execution is still pending and should not be recorded as successful until operator evidence exists.

Expected operator path:

1. Reload the production Parallax URL.
2. Confirm the 3D knot identity and perceptibly moving living surface are visible.
3. If an older conversation still shows a specification amendment while its Work Specification is approved, use `RESUME SCOPE` only when that approved contract is the scope to continue against.
4. For the bounded-autonomy execution test, switch to Code and start a fresh coding objective.
5. Capture and approve its Work Specification.
6. Confirm the Engineering Run reaches PLAN and shows `Run autonomously`.
7. Invoke `Run autonomously`.
8. Expected success path: protected PLAN evidence is created and the run advances to IMPLEMENT, then stops with `IMPLEMENTATION_REQUIRED`.
9. Expected safe-failure path: the run remains at PLAN with `EXECUTOR_UNAVAILABLE`, proving fail-closed Sandbox behavior.

Because the autonomy control is conditional on a bound Engineering Run, a fresh empty Code screen does not show the button before a coding objective, Work Specification, approval, and PLAN run exist.

## Deployment state vocabulary

- v0.13 bounded-autonomy implementation: **IMPLEMENTED / DEPLOYED**
- v0.13.1 active-spec production guard: **IMPLEMENTED / DEPLOYED**
- v0.13.2 visual integration: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.3 current-draft amendment release: **VALIDATED / DEPLOYED**
- v0.13.4 explicit approved-scope recovery: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Automated CI validation: **PASS**
- Merged to `main`: **YES**
- Production web: **READY / HTTP 200 VERIFIED**
- Production API: **READY / OPENAPI HTTP 200 VERIFIED**
- Private production authentication: **VERIFIED FAIL-CLOSED (401 unauthenticated)**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the v0.13.2 visual integration, v0.13.3 amendment lifecycle repair, v0.13.4 explicit recovery behavior, passing release gates, current main commit, production deployments, and deployment-verification evidence.
- `DESIGN-SYSTEM.md`: durably updated by v0.13.2 for the approved knot identity, perceptible ambient motion, Work Specification material, optical typesetter, and response-follow rules; no additional v0.13.4 design-system change was required.
- `ARCHITECTURE.md`: unchanged; v0.13.3 and v0.13.4 preserve existing persistence, trust boundaries, state ownership, authentication, Code binding, and bounded-autonomy architecture.
- `PROJECT-CONSTITUTION.md`: unchanged; the releases remain consistent with existing human-control, fail-closed, evidence, and authority principles.

Historical candidate, preview, CI, and deployment evidence remains preserved in Git and Vercel history.
