# Parallax 2.0 Current State

Version: 0.13.9 production
Date: 2026-08-22
Status: DEPLOYMENT-VERIFIED — APP-BUILDER WAVE 1 ACTIVE; REAL-DEVICE LIVE-EDGE CHECK AND FIRST REAL OPERATOR SANDBOX EXECUTION PENDING
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

The protected 390×844 browser acceptance verifies three distinct conditions:

1. Work Specification expansion preserves the live edge automatically;
2. a later non-streaming settled state/content mutation remains pinned to the live edge;
3. deliberate operator scroll-away remains preserved after another state/content mutation.

## Parallel ChatGPT development foundation — active

Parallax has a GitHub-authoritative concurrency model for development from multiple ChatGPT project conversations. The foundation was validated in PR `#39` and squash-merged as `b1d8679770e310f70f27628329855733f6b4ac80`.

The durable development-control model is:

- `PROJECT-CONSTITUTION.md` v1.1 establishes that parallel implementation is isolated and final integration is serialized;
- `PARALLEL-DEVELOPMENT.md` is the operating protocol for worker chats and the Integration / Control Tower chat;
- GitHub `[WS]` issues are the live scope/ownership ledger;
- each ACTIVE worker uses one bounded workstream and one isolated branch, declares owned/shared paths and dependencies before substantive implementation, and prepares a validated PR without merging/deploying by default;
- GitHub authoritative records, workstream issues, branches/PRs, CI/evaluation evidence, and deployment evidence outrank individual chat recollection for current development state;
- the Integration / Control Tower role is tracked in issue `#31` and serializes final merges, latest-main revalidation, deployment, and release-state maintenance.

The parallel-development foundation is governance/development infrastructure only. It does **not** change the v0.13.9 runtime, API, authentication, authorization, persistence, Code authority, database schema, or production deployment state.

## Dynamic workstream specification validation — active

Parallel development exposed a material validation gap in the historical `Parallax P2 CI` workflow: its specification checks were a hard-coded list and its DSPy release compilation still targeted `P2-V0.12.0`, so a new worker specification could receive otherwise-green repository checks without that new specification itself being protected-validated and DSPy-compiled.

PR `#52` closed that gap by adding `.github/workflows/workstream-spec-validation.yml`, the independent **Parallax Workstream Spec Validation** gate. The gate now:

- detects changed/new `specs/P2-*.md` files relative to the PR or push base;
- rejects changed workstream specifications that do not use the semantic `P2-Vx.y.z.md` identity convention;
- rejects deletion of versioned Parallax specification records;
- applies the protected specification contract to every changed semantic specification;
- for non-draft PRs and `main` pushes, executes DSPy SpecCritic + SpecCompiler for each changed specification and requires protected DSPy plan evidence;
- uploads changed-spec evidence for integration review;
- leaves historical specification records intact instead of retroactively requiring older patch-spec formats to satisfy a newer full-contract schema.

The first candidate intentionally attempted full historical-catalog validation and exposed that older patch-spec records predate the current protected contract. The corrected gate validates changed/new workstream specifications, preserving historical evidence while making all future parallel work fail closed on its own specification contract.

PR `#52` exact head `32522276f87466f4e1f468a04eb32dbac853ccec` passed all three repository workflows before squash merge as `83b6b6b418b9f2c87608b46a38cfe2026a4c0b25`:

- `Parallax Workstream Spec Validation` run `32599261876` — SUCCESS;
- `Parallax P2 CI` run `32599261852` — SUCCESS;
- `Bounded Autonomy Pilot` run `32599261860` — SUCCESS.

This is CI/governance infrastructure only; no Vercel deployment is required. Wave 1 worker PRs must refresh against `main` containing this gate and pass it before they are eligible for integration.

## App-builder Wave 1 — active

The app-builder acceleration program is tracked in issue `#32`, with Integration / Control Tower sequencing in issue `#31`. All four initial foundation workstreams are active:

- `#43` — App project lifecycle foundation — reserved spec `P2-V0.14.1`; owns canonical durable Project/App identity and persistence;
- `#44` — Safe source implementation and patch engine — reserved spec `P2-V0.14.2`; additive bounded source mutation/evidence primitive;
- `#45` — Project-scoped tool authority contracts — spec `P2-V0.14.3`; additive fail-closed capability and audit contracts;
- `#46` — App-builder evaluation and observability spine — spec `P2-V0.14.4`; additive protected app-builder benchmark/evidence contracts.

The scopes are intentionally separable. #44 and #45 may use temporary filesystem/opaque project references in isolated tests, but final production integration must bind to the canonical Project identity accepted from #43. #46 must reconcile its fixtures and observable field mappings to the accepted #43/#44/#45 contracts before protected app-builder CI integration.

Preferred Wave 1 integration order is #43 → #44 → #45 → #46. Every interacting candidate must refresh against latest relevant `main`, pass Parallax Workstream Spec Validation, P2 CI, and Bounded Autonomy Pilot, and receive Control Tower contract/diff review before merge.

Historical superseded PRs `#20`, `#15`, `#9`, `#4`, `#3`, and `#2` have been closed so they cannot be mistaken for current ownership or integration candidates.

GitHub `main` is still not branch-protected. Repository instructions, isolated workstream branches, PR discipline, dynamic workstream-spec validation, and CI provide the current enforcement layer; Control Tower continues to treat worker merge/deploy actions as prohibited until a GitHub-side ruleset can be enabled.

## Validation evidence

PR `#41`, head `43335654a7408594d7ff9a7ace8d509054ded80c`, passed both protected workflows before merge:

- `Parallax P2 CI` run `32591203005` — SUCCESS;
- `Bounded Autonomy Pilot` run `32591202996` — SUCCESS.

The passing v0.13.9 gate covered specification validation, full API regression tests, client typecheck/state/export, browser/Skia acceptance, mobile Work Specification geometry, iOS keyboard-visible viewport behavior, in-flow composer/live-edge acceptance, settled non-streaming live-edge following, deliberate operator scroll-away preservation, protected Engineering/Reason/Code promotion evaluation, DSPy release compilation, and bounded-autonomy authority regressions.

The passing client build-evidence artifact is `9480385338`. Evaluation evidence is `9480375194`, and DSPy development evidence is `9480389182`.

PR `#41` was squash-merged to `main` as application commit `0938296be2c8b488340717fd5f6dbffad65d3856`.

Parallel-development foundation PR `#39`, head `fb392b476a45795a059da09edebb0f84e57fc68e`, passed both repository workflows before merge:

- `Parallax P2 CI` run `32590999199` — SUCCESS across API/contracts, client/typecheck/state/export/browser/Skia, protected promotion evaluation, and DSPy release compilation;
- `Bounded Autonomy Pilot` run `32590999173` — SUCCESS across protected execution/autonomy API regression and client validation.

PR `#48` then recorded the governance decision in this authoritative state record after full repository validation and was squash-merged as `f4b318d7fc1e772dfce2054321661f320e0f1336`.

Dynamic workstream-spec validation PR `#52` passed Workstream Spec Validation `32599261876`, P2 CI `32599261852`, and Bounded Autonomy Pilot `32599261860` before merge as `83b6b6b418b9f2c87608b46a38cfe2026a4c0b25`.

Because PRs `#39`, `#48`, and `#52` change development governance/validation records rather than application runtime, no production deployment is required for those material decisions.

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

Authentication, amendment recovery, Engineering Run behavior, and bounded-autonomy authority are unchanged by v0.13.5–v0.13.9 and by the parallel-development governance/CI work.

## Remaining operator verification

Automated v0.13.9 validation and production deployment verification are complete. Two user-driven checks remain intentionally unclaimed:

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
- Dynamic workstream specification validation: **VALIDATED / MERGED / CI-ACTIVE**
- App-builder Wave 1 foundations: **ACTIVE / NOT YET INTEGRATED**
- Automated runtime CI validation: **PASS**
- Merged application release to `main`: **YES — v0.13.9**
- Production web: **READY / HTTP 200 VERIFIED**
- Production API: **UNCHANGED FROM v0.13.4 / READY**
- Private production authentication: **UNCHANGED / FAIL-CLOSED**
- Real-device v0.13.9 live-edge behavior: **PENDING OPERATOR CHECK**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the deployment-verified v0.13.9 runtime baseline, validated/merged parallel ChatGPT development governance, dynamic workstream-spec validation, and active app-builder Wave 1 control state. The production application version remains v0.13.9 because the governance/CI changes do not alter runtime behavior.
- `PROJECT-CONSTITUTION.md`: v1.1; unchanged by the dynamic spec gate. PR #39 already established GitHub-authoritative isolated parallel development and serialized integration as a durable governing principle.
- `DESIGN-SYSTEM.md`: unchanged; no visual or interaction principle changed.
- `ARCHITECTURE.md`: unchanged at v2.1; the dynamic spec gate and Wave 1 control state are development-governance/validation concerns and do not yet change deployed runtime persistence, service boundaries, authentication, Code binding, or bounded-autonomy architecture. Architecture should change when accepted Wave 1 runtime contracts are integrated.

Historical candidate, preview, CI, deployment, workstream, and visual evidence remains preserved in GitHub Actions, GitHub issues/PRs, and Vercel history.
