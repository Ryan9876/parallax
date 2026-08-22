# Parallax 2.0 Current State

Version: 0.13.5 production
Date: 2026-08-22
Status: DEPLOYMENT-VERIFIED — FIRST REAL OPERATOR SANDBOX EXECUTION STILL PENDING
Production branch: `main`
Production application commit: `fef3bfc997159ca8dfdc1502631c3e9dc92b7115`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_BnPdT8694MZo6HmceSBPCvqGphiA`
Production API deployment: `dpl_G5hz69cCs877NE2kkuPGLMweaHuK`

## Current production baseline

Parallax 2.0 v0.13.5 is merged to `main` and deployment-verified on the production web project. The current baseline combines the v0.13 bounded-autonomy pilot, v0.13.1 active-spec production guard, v0.13.2 visual integration, v0.13.3 amendment-approval lifecycle repair, v0.13.4 explicit approved-scope recovery, and v0.13.5 mobile Work Specification review correction.

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

The production workspace uses the approved Parallax visual language:

- transparent glossy 3D interlocking-knot identity in primary and assistant-avatar use;
- perceptibly animated Ambient Chroma Flow / living surface during normal 5–15 second observation;
- rounded translucent Work Specification material;
- compact stream-synchronized optical engraving treatment for active assistant responses;
- response-follow behavior that keeps live output visible while respecting intentional upward scrolling;
- composer-height clearance so active content is not hidden behind the input surface;
- mobile geometry and controls validated without horizontal overflow.

The durable knot, ambient-motion, Work Specification material, optical-typesetter, and response-follow rules are recorded in `DESIGN-SYSTEM.md`.

## v0.13.3 amendment approval lifecycle — live

A material scope change correctly moves a conversation to `SPEC_AMENDMENT`. Approving the **current replacement DRAFT** returns that conversation to `ACTIVE` only after specification approval succeeds.

The guard remains narrow: the conversation must already be `SPEC_AMENDMENT`, the specification must still be the latest `DRAFT`, and re-approving an older already-approved specification cannot bypass a newer amendment stop.

## v0.13.4 explicit approved-scope recovery — live

For persisted `SPEC_AMENDMENT` conversations whose latest Work Specification is already `APPROVED`, Parallax exposes explicit human recovery rather than timestamp inference or silent migration:

- the Work Specification surface offers `RESUME SCOPE` only for the recoverable state;
- the API exposes `POST /v1/conversations/{conversation_id}/work-specifications/resume-approved-scope`;
- the server permits the transition only when the conversation is currently `SPEC_AMENDMENT` and its latest Work Specification is `APPROVED`;
- if the latest Work Specification is a `DRAFT`, recovery is rejected and normal approval is required;
- success changes only conversation status to `ACTIVE`.

## v0.13.5 mobile Work Specification review — live

A production phone screenshot exposed a layout regression on an expanded Work Specification: the governed surface could consume most of a 390×844-class viewport and visually collide with the persistent composer.

v0.13.5 corrects that behavior without changing specification authority or lifecycle semantics:

- expanded Work Specification details are height-bounded on compact viewports;
- long contract content scrolls inside the specification body instead of extending through the conversation workspace;
- title, status, revision, approval/refresh controls, and disclosure control remain visible while the details scroll;
- the redundant compact objective preview is suppressed while expanded, reducing vertical waste;
- approval collapses the expanded review state;
- phone controls remain at least 44 px;
- the Work Specification surface remains above and separate from the persistent composer.

A dedicated 390×844 Playwright acceptance test now asserts non-overlap, internal scrolling, and control-target geometry. CI visual evidence includes `mobile-spec-expanded.png`, which shows the corrected production composition before promotion.

The `P2-V0.13.0` text visible in the workspace header is the active product specification identifier for the conversation, not the deployed application release number. Its presence in a v0.13.5 UI is therefore expected and is not version drift.

## Validation evidence

PR `#26`, head `d03d5cf592b4c13f3a97ad34109f5c11704d7731`, passed both protected workflows before merge:

- `Parallax P2 CI` run `32587644965` — SUCCESS;
- `Bounded Autonomy Pilot` run `32587644971` — SUCCESS.

The passing gate covered:

- specification validation;
- full API regression tests;
- client typecheck;
- response-state tests;
- web export;
- browser / Skia acceptance;
- dedicated mobile Work Specification geometry acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy release compilation;
- bounded-autonomy authority-boundary regressions.

The client build-evidence artifact for the passing CI run is `9479494500` and contains the validated `mobile-spec-expanded.png` evidence.

PR `#26` was squash-merged to `main` as `fef3bfc997159ca8dfdc1502631c3e9dc92b7115`.

## Deployment verification

### Web

Production deployment `dpl_BnPdT8694MZo6HmceSBPCvqGphiA` is READY, targets production, and carries main commit `fef3bfc997159ca8dfdc1502631c3e9dc92b7115`.

Its aliases include:

- `parallax-ashy-one-20.vercel.app`;
- `parallax-lew7.vercel.app`;
- `parallax-git-main-lew7.vercel.app`.

A direct request to `https://parallax-ashy-one-20.vercel.app/` returned HTTP 200 after the deployment and served the current production web bundle.

### API

v0.13.5 contains no API implementation change. The API project deployment attempt for main commit `fef3bfc997159ca8dfdc1502631c3e9dc92b7115` (`dpl_DTS1m1JvwfMPwRWDGVnc1GY4jNMD`) was canceled rather than producing a new API release.

The deployment-verified v0.13.4 API deployment `dpl_G5hz69cCs877NE2kkuPGLMweaHuK` remains the production API behind `parallax-api-tan.vercel.app`. Its authentication, amendment recovery endpoint, Engineering Run behavior, and bounded-autonomy authority are unchanged by v0.13.5.

## Remaining operator verification

The current web release is deployed and automated validation is complete. The first real user-driven isolated Sandbox execution is still pending and should not be recorded as successful until operator evidence exists.

Expected operator path:

1. Reload the production Parallax URL.
2. On mobile, expand the Work Specification and confirm its details scroll inside the panel while the composer remains unobstructed.
3. If an older conversation still shows a specification amendment while its Work Specification is approved, use `RESUME SCOPE` only when that approved contract is the scope to continue against.
4. For the bounded-autonomy execution test, switch to Code and start a fresh coding objective.
5. Capture and approve its Work Specification.
6. Confirm the Engineering Run reaches PLAN and shows `Run autonomously`.
7. Invoke `Run autonomously`.
8. Expected success path: protected PLAN evidence is created and the run advances to IMPLEMENT, then stops with `IMPLEMENTATION_REQUIRED`.
9. Expected safe-failure path: the run remains at PLAN with `EXECUTOR_UNAVAILABLE`, proving fail-closed Sandbox behavior.

## Deployment state vocabulary

- v0.13 bounded-autonomy implementation: **IMPLEMENTED / DEPLOYED**
- v0.13.1 active-spec production guard: **IMPLEMENTED / DEPLOYED**
- v0.13.2 visual integration: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.3 current-draft amendment release: **VALIDATED / DEPLOYED**
- v0.13.4 explicit approved-scope recovery: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.5 mobile Work Specification review correction: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Automated CI validation: **PASS**
- Merged to `main`: **YES**
- Production web: **READY / HTTP 200 VERIFIED**
- Production API: **UNCHANGED FROM v0.13.4 / READY**
- Private production authentication: **UNCHANGED / FAIL-CLOSED**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the v0.13.5 mobile regression correction, passing validation evidence, merge commit, production web deployment, and deployment verification.
- `DESIGN-SYSTEM.md`: unchanged; v0.13.5 enforces existing conversation-first, expansion/collapse, composer-clearance, and 44 pt mobile-control rules rather than introducing a new visual-language rule.
- `ARCHITECTURE.md`: unchanged; no persistence, state ownership, trust-boundary, authentication, Code-binding, or bounded-autonomy architecture changed.
- `PROJECT-CONSTITUTION.md`: unchanged; the correction remains consistent with existing human-control, fail-closed, evidence, accessibility, and authority principles.

Historical candidate, preview, CI, and deployment evidence remains preserved in Git and Vercel history.
