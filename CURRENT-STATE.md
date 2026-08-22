# Parallax 2.0 Current State

Version: 0.13.7 production
Date: 2026-08-22
Status: DEPLOYMENT-VERIFIED — REAL-DEVICE COMPOSER CHECK AND FIRST REAL OPERATOR SANDBOX EXECUTION PENDING
Production branch: `main`
Production application commit: `c3901d01eb5dedb0f791b9750c39520a979be39d`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_7dHwT7QB7t9XvJ8rdk8SQeiAyTt3`
Production API deployment: `dpl_G5hz69cCs877NE2kkuPGLMweaHuK`

## Current production baseline

Parallax 2.0 v0.13.7 is merged to `main` and deployment-verified on the production web project. The current baseline combines the v0.13 bounded-autonomy pilot, v0.13.1 active-spec production guard, v0.13.2 visual integration, v0.13.3 amendment-approval lifecycle repair, v0.13.4 explicit approved-scope recovery, v0.13.5 mobile Work Specification review correction, v0.13.6 iOS keyboard-visible workspace correction, and v0.13.7 structural composer-clearance correction.

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
- mobile geometry and controls validated without horizontal overflow.

The durable knot, ambient-motion, Work Specification material, optical-typesetter, response-follow, mobile keyboard, and composer-clearance rules are recorded in `DESIGN-SYSTEM.md`.

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

v0.13.5 height-bounds expanded Work Specification details on compact viewports, keeps the summary/actions visible, allows long contract content to scroll inside the specification body, and preserves 44 px phone targets.

The `P2-V0.13.0` text visible in the workspace header is the active product specification identifier for the conversation, not the deployed application release number.

## v0.13.6 iOS keyboard-visible workspace — live

A production iPhone screenshot exposed two WebKit-specific problems when the composer received focus: the software keyboard could overlay the composer, and 14 px input text could trigger Safari automatic focus zoom.

v0.13.6 corrected those behaviors without changing application authority semantics:

- phone-sized web editable text is forced to at least 16 CSS px;
- a measured `visualViewport` guard fits the Parallax root to the visible area when the keyboard overlays WebKit content;
- non-zero visual viewport offsets are compensated;
- the adjustment resets when the viewport recovers or editable focus ends;
- no hard-coded iPhone or keyboard height is used.

The v0.13.6 keyboard regression remains part of the protected browser suite and continues to pass under v0.13.7.

## v0.13.7 in-flow composer clearance — live

A subsequent production iPhone screenshot with the keyboard closed exposed the deeper layout problem: the composer itself was still absolutely positioned over the conversation thread. The client attempted to avoid overlap by measuring composer height and adding estimated bottom padding, but newest assistant/amendment content could still render underneath the composer after governed-surface and state changes.

v0.13.7 replaces that estimation model with structural layout ownership:

- the composer is an in-flow dock that reserves actual vertical space in both the normal Skia workspace and reduced-graphics fallback;
- the conversation thread is the flexible, shrinkable scroll region between governed surfaces and the composer;
- the main/thread flex regions explicitly permit shrinking so an expanded Work Specification does not push the composer over narrative content;
- estimated composer-height padding is no longer the primary clearance mechanism;
- at the thread live edge, newest assistant and amendment content remains reachable above the composer;
- v0.13.6 keyboard-visible visual-viewport handling remains unchanged and continues to operate around the in-flow composer.

This is the stronger structural correction: layout geometry now prevents overlap rather than attempting to compensate for an overlay after measurement.

## Validation evidence

PR `#28`, head `3a8a7d5ba6293800601fa053b30a036bb106cc3a`, passed both protected workflows before merge:

- `Parallax P2 CI` run `32589939080` — SUCCESS;
- `Bounded Autonomy Pilot` run `32589939139` — SUCCESS.

The passing gate covered:

- specification validation;
- full API regression tests;
- client typecheck;
- response-state tests;
- web export;
- browser / Skia acceptance;
- existing mobile Work Specification geometry acceptance;
- existing iOS keyboard-visible viewport acceptance;
- new 390×844 composer-clearance acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy release compilation;
- bounded-autonomy authority-boundary regressions.

The new composer-clearance regression uses an expanded draft Work Specification plus a user turn and newest assistant response, scrolls the conversation to the live edge, and asserts that neither the response nor governed surface intersects the composer. The passing client build-evidence artifact is `9480060187` and includes `mobile-composer-clearance.png` alongside the existing mobile keyboard/spec evidence.

PR `#28` was squash-merged to `main` as application commit `c3901d01eb5dedb0f791b9750c39520a979be39d`.

## Deployment verification

### Web

Production deployment `dpl_7dHwT7QB7t9XvJ8rdk8SQeiAyTt3` is READY, targets production, and carries application commit `c3901d01eb5dedb0f791b9750c39520a979be39d`.

Its aliases include:

- `parallax-ashy-one-20.vercel.app`;
- `parallax-lew7.vercel.app`;
- `parallax-git-main-lew7.vercel.app`.

A direct request to `https://parallax-ashy-one-20.vercel.app/` returned HTTP 200 after deployment and served the new production web bundle `index-5713fb3fa9aaa53907ce61b0c2fc97e3.js`.

Later documentation-only commits update authoritative records but do not replace the production application commit above.

### API

v0.13.7 contains no API implementation change. The deployment-verified v0.13.4 API deployment `dpl_G5hz69cCs877NE2kkuPGLMweaHuK` remains the production API behind `parallax-api-tan.vercel.app`.

Authentication, amendment recovery, Engineering Run behavior, and bounded-autonomy authority are unchanged by v0.13.5–v0.13.7.

## Remaining operator verification

Automated validation and production deployment verification are complete. Two user-driven checks remain intentionally unclaimed:

1. **Real-device mobile composition:** reload production on the iPhone and confirm the newest response remains fully scrollable above the composer with the keyboard closed, then focus the composer and confirm the v0.13.6 keyboard-visible behavior still feels correct on-device.
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
- v0.13.7 in-flow composer-clearance correction: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Automated CI validation: **PASS**
- Merged application release to `main`: **YES**
- Production web: **READY / HTTP 200 VERIFIED**
- Production API: **UNCHANGED FROM v0.13.4 / READY**
- Private production authentication: **UNCHANGED / FAIL-CLOSED**
- Real-device v0.13.7 mobile composition: **PENDING OPERATOR CHECK**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the v0.13.7 structural composer-clearance correction, passing validation evidence, merge commit, production deployment, and remaining on-device/operator checks.
- `DESIGN-SYSTEM.md`: advanced to v2.1 because v0.13.7 establishes a durable interaction/layout rule: the composer is an in-flow dock, the thread is the shrinkable scroll region, and narrative clearance is structural rather than estimated from overlay height.
- `ARCHITECTURE.md`: unchanged; v0.13.7 changes client layout ownership but not persistence, service boundaries, authentication, state ownership, Code binding, or bounded-autonomy architecture.
- `PROJECT-CONSTITUTION.md`: unchanged; the release remains consistent with existing accessibility, human-control, fail-closed, evidence, and authority principles.

Historical candidate, preview, CI, deployment, and visual evidence remains preserved in GitHub Actions and Vercel history.
