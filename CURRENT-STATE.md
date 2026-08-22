# Parallax 2.0 Current State

Version: 0.13.6 production
Date: 2026-08-22
Status: DEPLOYMENT-VERIFIED — ON-DEVICE iOS KEYBOARD CHECK AND FIRST REAL OPERATOR SANDBOX EXECUTION PENDING
Production branch: `main`
Production application commit: `db25306a4aa76ce367ae7b4a5ab2dddccb3f6f40`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_8xQehA2gv25HC3ChuWQCfHmADFAs`
Production API deployment: `dpl_G5hz69cCs877NE2kkuPGLMweaHuK`

## Current production baseline

Parallax 2.0 v0.13.6 is merged to `main` and deployment-verified on the production web project. The current baseline combines the v0.13 bounded-autonomy pilot, v0.13.1 active-spec production guard, v0.13.2 visual integration, v0.13.3 amendment-approval lifecycle repair, v0.13.4 explicit approved-scope recovery, v0.13.5 mobile Work Specification review correction, and v0.13.6 iOS keyboard-visible workspace correction.

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

The durable knot, ambient-motion, Work Specification material, optical-typesetter, response-follow, and mobile keyboard rules are recorded in `DESIGN-SYSTEM.md`.

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

A dedicated 390×844 Playwright acceptance test asserts non-overlap, internal scrolling, and control-target geometry.

The `P2-V0.13.0` text visible in the workspace header is the active product specification identifier for the conversation, not the deployed application release number. Its presence in a v0.13.6 UI is expected and is not version drift.

## v0.13.6 iOS keyboard-visible workspace — live

A second production phone screenshot exposed two WebKit-specific mobile problems when the composer received focus:

1. the iOS software keyboard overlaid the layout viewport and could cover Parallax's persistent composer;
2. the 14 px composer text could trigger Safari automatic focus zoom, enlarging/cropping the workspace while typing.

v0.13.6 introduces a web-only correction without changing application state or authority semantics:

- phone-sized web editable text is forced to at least 16 CSS px, preventing Safari focus zoom while leaving normal user zoom enabled;
- a lightweight visual-viewport guard activates only when an editable field is focused and WebKit reports a materially reduced visible viewport;
- the Parallax root temporarily fits `visualViewport.height` and compensates `visualViewport.offsetTop`, keeping the workspace aligned with the actually visible region;
- the persistent composer therefore remains above the overlaid software keyboard;
- the guard restores the original root geometry as soon as the visual viewport recovers or editable focus ends;
- browsers that already resize their layout viewport correctly do not receive unnecessary compensation;
- no hard-coded iPhone or keyboard height is used.

The durable rule is now recorded in `DESIGN-SYSTEM.md` v2.0: phone web editables remain at least 16 CSS px, and keyboard-visible layout follows measured visual-viewport geometry rather than disabling zoom or assuming a device height.

## Validation evidence

PR `#27`, head `b6aecd5ea4b62755ba89a50a866f3a4c0801a8b8`, passed both protected workflows before merge:

- `Parallax P2 CI` run `32589040037` — SUCCESS;
- `Bounded Autonomy Pilot` run `32589040034` — SUCCESS.

The passing gate covered:

- specification validation;
- full API regression tests;
- client typecheck;
- response-state tests;
- web export;
- browser / Skia acceptance;
- existing mobile Work Specification geometry acceptance;
- new iOS keyboard-visible viewport acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy release compilation;
- bounded-autonomy authority-boundary regressions.

The new keyboard acceptance simulates a 390×844 layout viewport with a 480 px visible visual viewport and a 72 px visual-viewport offset while the composer is focused. It verifies:

- mobile editable computed font size is at least 16 px;
- the Parallax root fits the 480 px visible viewport;
- the 72 px offset is compensated;
- the composer remains entirely inside the visible region above the simulated keyboard;
- normal root geometry is restored after the viewport recovers.

The passing client build-evidence artifact is `9479833204` and contains `mobile-keyboard-visible.png` plus the existing visual evidence set.

PR `#27` was squash-merged to `main` as `db25306a4aa76ce367ae7b4a5ab2dddccb3f6f40`.

## Deployment verification

### Web

Production deployment `dpl_8xQehA2gv25HC3ChuWQCfHmADFAs` is READY, targets production, and carries main application commit `db25306a4aa76ce367ae7b4a5ab2dddccb3f6f40`.

Its aliases include:

- `parallax-ashy-one-20.vercel.app`;
- `parallax-lew7.vercel.app`;
- `parallax-git-main-lew7.vercel.app`.

A direct request to `https://parallax-ashy-one-20.vercel.app/` returned HTTP 200 after deployment and served the new production web bundle (`index-0a892c7b98c23432a3a42202da83d302.js`).

### API

v0.13.6 contains no API implementation change. The deployment-verified v0.13.4 API deployment `dpl_G5hz69cCs877NE2kkuPGLMweaHuK` remains the production API behind `parallax-api-tan.vercel.app`.

Its authentication, amendment recovery endpoint, Engineering Run behavior, and bounded-autonomy authority are unchanged by v0.13.5 and v0.13.6.

## Remaining operator verification

Automated validation and production deployment verification are complete. Two user-driven checks remain intentionally unclaimed:

1. **On-device iOS keyboard check:** reload production on the iPhone, tap the composer, and confirm the page no longer zooms/crops and the full composer remains immediately above the keyboard.
2. **First real isolated Sandbox execution:** complete the bounded-autonomy operator path below.

Expected autonomy path:

1. Reload the production Parallax URL.
2. Switch to Code and start a fresh coding objective.
3. Capture and approve its Work Specification.
4. Confirm the Engineering Run reaches PLAN and shows `Run autonomously`.
5. Invoke `Run autonomously`.
6. Expected success path: protected PLAN evidence is created and the run advances to IMPLEMENT, then stops with `IMPLEMENTATION_REQUIRED`.
7. Expected safe-failure path: the run remains at PLAN with `EXECUTOR_UNAVAILABLE`, proving fail-closed Sandbox behavior.

## Deployment state vocabulary

- v0.13 bounded-autonomy implementation: **IMPLEMENTED / DEPLOYED**
- v0.13.1 active-spec production guard: **IMPLEMENTED / DEPLOYED**
- v0.13.2 visual integration: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.3 current-draft amendment release: **VALIDATED / DEPLOYED**
- v0.13.4 explicit approved-scope recovery: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.5 mobile Work Specification review correction: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.6 iOS keyboard-visible workspace correction: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Automated CI validation: **PASS**
- Merged application release to `main`: **YES**
- Production web: **READY / HTTP 200 VERIFIED**
- Production API: **UNCHANGED FROM v0.13.4 / READY**
- Private production authentication: **UNCHANGED / FAIL-CLOSED**
- Real-device iOS keyboard behavior after v0.13.6: **PENDING OPERATOR CHECK**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the v0.13.6 iOS keyboard-visible correction, validation evidence, merge commit, production deployment, and remaining real-device/operator checks.
- `DESIGN-SYSTEM.md`: advanced to v2.0 because v0.13.6 introduces durable mobile-web rules for 16 px editable text, visual-viewport keyboard handling, preservation of user zoom, and measured keyboard-visible geometry.
- `ARCHITECTURE.md`: unchanged; the correction is a web presentation/runtime viewport adaptation and does not change persistence, state ownership, trust boundaries, authentication, Code binding, or bounded-autonomy architecture.
- `PROJECT-CONSTITUTION.md`: unchanged; the release remains consistent with existing accessibility, human-control, fail-closed, evidence, and authority principles.

Historical candidate, preview, CI, deployment, and visual evidence remains preserved in GitHub Actions and Vercel history.
