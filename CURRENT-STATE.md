# Parallax 2.0 Current State

Version: 0.13.9 production
Date: 2026-08-22
Status: DEPLOYMENT-VERIFIED — REAL-DEVICE LIVE-EDGE CHECK AND FIRST REAL OPERATOR SANDBOX EXECUTION PENDING
Production branch: `main`
Production application commit: `0938296be2c8b488340717fd5f6dbffad65d3856`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy`
Production API deployment: `dpl_G5hz69cCs877NE2kkuPGLMweaHuK`

## Current production baseline

Parallax 2.0 v0.13.9 is merged to `main` and deployment-verified on the production web project. The current baseline combines the v0.13 bounded-autonomy pilot, v0.13.1 active-spec production guard, v0.13.2 visual integration, v0.13.3 amendment-approval lifecycle repair, v0.13.4 explicit approved-scope recovery, v0.13.5 mobile Work Specification review correction, v0.13.6 iOS keyboard-visible workspace correction, v0.13.7 structural composer-clearance correction, v0.13.8 live-edge continuity correction, and v0.13.9 live-edge hardening.

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

## Visual and interaction baseline

The production workspace uses the approved Parallax visual language and interaction model:

- transparent glossy 3D interlocking-knot identity in primary and assistant-avatar use;
- perceptibly animated Ambient Chroma Flow / living surface during normal 5–15 second observation;
- rounded translucent Work Specification material;
- compact stream-synchronized optical engraving treatment for active assistant responses;
- response-follow behavior that keeps live output visible while respecting intentional upward scrolling;
- mobile geometry and controls validated without horizontal overflow;
- phone-sized web editable text at a minimum of 16 CSS px to avoid Safari focus zoom;
- measured iOS `visualViewport` handling so the composer remains above the software keyboard;
- an in-flow composer that reserves structural layout space instead of overlaying conversation content.

The durable visual, mobile-keyboard, composer-clearance, and conversation-follow rules are recorded in `DESIGN-SYSTEM.md`.

## Specification and amendment lifecycle — live

Material scope changes move a conversation to `SPEC_AMENDMENT`. Approving the current replacement DRAFT returns that conversation to `ACTIVE` only after specification approval succeeds. Re-approving an older already-approved specification cannot bypass a newer amendment stop.

For persisted `SPEC_AMENDMENT` conversations whose latest Work Specification is already `APPROVED`, Parallax exposes explicit human recovery through `RESUME SCOPE` and `POST /v1/conversations/{conversation_id}/work-specifications/resume-approved-scope`. Recovery is allowed only when the conversation is currently `SPEC_AMENDMENT` and the latest specification is `APPROVED`; DRAFT specifications still require normal approval.

## v0.13.7 in-flow composer clearance — live

A production iPhone screenshot showed that an absolutely positioned composer could still cover newest assistant/amendment content after governed-surface and state changes. v0.13.7 replaced that estimation model with structural layout ownership:

- the composer is an in-flow dock that reserves actual vertical space in both normal and reduced-graphics modes;
- the conversation thread is the flexible, shrinkable scroll region between governed surfaces and the composer;
- main/thread flex regions explicitly permit shrinking;
- estimated composer-height padding is no longer the primary clearance mechanism;
- v0.13.6 keyboard-visible visual-viewport handling remains unchanged around the in-flow composer.

## v0.13.8 live-edge continuity — live

The first real-device check after v0.13.7 confirmed structural composer clearance but showed that the newest settled assistant response could remain below the visible thread after Work Specification or amendment-state layout changes.

v0.13.8 added a web live-edge continuity guard that identifies the actual conversation scroll region from the latest assistant response. While the operator remains within 120 px of the live edge, content mutations and thread-region resizes restore the thread to the newest content. Sending a message re-arms following, while deliberate operator scroll-away disables automatic pinning until the operator returns near the live edge or sends another message.

## v0.13.9 live-edge hardening — live

v0.13.9 hardens the v0.13.8 behavior for delayed mobile layout settling and thread lifecycle changes without altering application authority or the structural composer model:

- live-edge pinning now performs the immediate animation-frame correction, a second animation-frame correction, and a 120 ms settled correction so delayed WebKit/layout changes do not strand the newest response;
- the settled correction still checks the live-edge armed state, so an operator who scrolls away during that interval is not pulled back down;
- stale scroll listeners are removed when Parallax binds a different conversation scroll region;
- starting a new conversation explicitly re-arms live-edge following in addition to sending a message;
- resize and orientation changes schedule a live-edge correction only while following is armed;
- keyboard viewport handling, Work Specification authority, amendment semantics, Engineering Runs, authentication, and bounded-autonomy authority are unchanged.

The protected 390×844 browser acceptance now verifies three distinct conditions:

1. Work Specification expansion preserves the live edge automatically;
2. a later non-streaming settled state/content mutation remains pinned to the live edge;
3. deliberate operator scroll-away remains preserved after another state/content mutation.

## Parallel ChatGPT development foundation — active

Parallax now has a GitHub-authoritative concurrency model for development from multiple ChatGPT project conversations. The foundation was validated in PR `#39` and squash-merged as `b1d8679770e310f70f27628329855733f6b4ac80`.

The durable development-control model is:

- `PROJECT-CONSTITUTION.md` v1.1 establishes that parallel implementation is isolated and final integration is serialized;
- `PARALLEL-DEVELOPMENT.md` is the operating protocol for worker chats and the Integration / Control Tower chat;
- open GitHub `[WS]` issues are the live scope/ownership ledger;
- each ACTIVE worker uses one bounded workstream and one isolated branch, declares owned/shared paths and dependencies before substantive implementation, and prepares a validated PR without merging/deploying by default;
- GitHub authoritative records, workstream issues, branches/PRs, CI/evaluation evidence, and deployment evidence outrank individual chat recollection for current development state;
- the Integration / Control Tower role is tracked in issue `#31` and serializes final merges, latest-main revalidation, deployment, and release-state maintenance.

The parallel-development foundation is governance/development infrastructure only. It does **not** change the v0.13.9 runtime, API, authentication, authorization, persistence, Code authority, database schema, or production deployment state.

The app-builder acceleration program is tracked in issue `#32`. Its initial parallel Wave 1 workstreams are planned as:

- `#43` — App project lifecycle foundation;
- `#44` — Safe source implementation and patch engine;
- `#45` — Project-scoped tool authority contracts;
- `#46` — App-builder evaluation and observability spine.

These workstreams are intentionally additive and separable where possible. Workers must still refresh their exact path reservations against current open work before changing code. The immediate critical path to usable app-building is first-class Project isolation plus safe bounded source implementation; tool authority and protected app-builder evaluation can advance alongside those contracts.

## Validation evidence

PR `#41`, head `43335654a7408594d7ff9a7ace8d509054ded80c`, passed both protected workflows before merge:

- `Parallax P2 CI` run `32591203005` — SUCCESS;
- `Bounded Autonomy Pilot` run `32591202996` — SUCCESS.

The passing gate covered:

- specification validation;
- full API regression tests;
- client typecheck;
- response-state tests;
- web export;
- browser / Skia acceptance;
- mobile Work Specification geometry acceptance;
- iOS keyboard-visible viewport acceptance;
- in-flow composer/live-edge acceptance;
- settled non-streaming live-edge follow acceptance;
- deliberate operator scroll-away preservation;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy release compilation;
- bounded-autonomy authority-boundary regressions.

The passing client build-evidence artifact is `9480385338`. Evaluation evidence is `9480375194`, and DSPy development evidence is `9480389182`.

PR `#41` was squash-merged to `main` as application commit `0938296be2c8b488340717fd5f6dbffad65d3856`.

Parallel-development foundation PR `#39`, head `fb392b476a45795a059da09edebb0f84e57fc68e`, also passed both repository workflows before merge:

- `Parallax P2 CI` run `32590999199` — SUCCESS across API/contracts, client/typecheck/state/export/browser/Skia, protected promotion evaluation, and DSPy release compilation;
- `Bounded Autonomy Pilot` run `32590999173` — SUCCESS across protected execution/autonomy API regression and client validation.

Because PR `#39` changed only governance, documentation, issue/PR templates, and the approved `P2-V0.14.0` development-control specification, no runtime deployment was required for that material decision.

## Deployment verification

### Web

Production deployment `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` is READY, targets production, and carries application commit `0938296be2c8b488340717fd5f6dbffad65d3856`.

Its aliases include:

- `parallax-ashy-one-20.vercel.app`;
- `parallax-lew7.vercel.app`;
- `parallax-git-main-lew7.vercel.app`.

A direct request to `https://parallax-ashy-one-20.vercel.app/` returned HTTP 200 after deployment and served the v0.13.9 production web bundle `index-f3d96ca54c0591b0267e0cc46400b017.js`.

### API

v0.13.9 contains no API implementation change. The deployment-verified v0.13.4 API deployment `dpl_G5hz69cCs877NE2kkuPGLMweaHuK` remains the production API behind `parallax-api-tan.vercel.app`.

Authentication, amendment recovery, Engineering Run behavior, and bounded-autonomy authority are unchanged by v0.13.5–v0.13.9.

## Remaining operator verification

Automated validation and production deployment verification are complete. Two user-driven checks remain intentionally unclaimed:

1. **Real-device live-edge composition:** reload production on the iPhone and confirm the newest assistant response automatically remains visible above the composer after Work Specification/amendment state changes, while intentional upward scrolling remains respected.
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
- v0.13.8 live-edge continuity correction: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- v0.13.9 live-edge hardening: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Parallel ChatGPT development foundation: **VALIDATED / MERGED / GOVERNANCE-ACTIVE**
- Automated CI validation: **PASS**
- Merged application release to `main`: **YES**
- Production web: **READY / HTTP 200 VERIFIED**
- Production API: **UNCHANGED FROM v0.13.4 / READY**
- Private production authentication: **UNCHANGED / FAIL-CLOSED**
- Real-device v0.13.9 live-edge behavior: **PENDING OPERATOR CHECK**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the v0.13.9 deployment-verified runtime baseline and the validated/merged parallel ChatGPT development governance decision, including the app-builder Wave 1 control plan. The production application version remains v0.13.9 because the parallel-development foundation does not change runtime behavior.
- `PROJECT-CONSTITUTION.md`: v1.1; updated by PR #39 to make GitHub-authoritative isolated parallel development and serialized integration a durable governing principle.
- `DESIGN-SYSTEM.md`: unchanged by the parallel-development foundation; v0.13.9 only hardens the existing documented conversation-follow rule.
- `ARCHITECTURE.md`: unchanged by the parallel-development foundation; concurrency control is a development-governance concern and does not change runtime persistence, service boundaries, authentication, state ownership, Code binding, or bounded-autonomy architecture.

Historical candidate, preview, CI, deployment, workstream, and visual evidence remains preserved in GitHub Actions, GitHub issues/PRs, and Vercel history.
