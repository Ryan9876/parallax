# Parallax 2.0 Current State

Version: 0.13.0 preview candidate
Date: 2026-08-22
Status: VALIDATED PREVIEW — OPERATOR SANDBOX TEST PENDING
Candidate branch: `p2/v0.13.0-bounded-autonomy`
Candidate head: `7f5178cec5cac755ff15e8369629e6127bff57e8`
Pull request: `#19` — ready for review, mergeable, not merged
Production release: v0.12.0 remains unchanged and deployment-verified
Production branch: `main`
Production application release commit: `7d86aa3e9ae1dd096cf4712b786ccf4c2534b6a5`
Production web deployment: `dpl_9RZi4PQzYZpezwGcG4vUhiC7fQib`
Production API deployment: `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`

## Current candidate

Parallax 2.0 v0.13.0 — **Bounded Autonomy Pilot** — is implemented and deployed to Vercel preview for operator testing. It is not merged to `main` and has not been promoted to production.

The approved product specification is `P2-V0.13.0`. The candidate introduces the first live isolated execution plane for Code while preserving explicit authority boundaries. A user can request a bounded autonomous cycle from the existing Code run surface; the server, not the client or model, owns the executable command registry, acceptance map, stage transitions, and stop conditions.

The pilot grants autonomous authority only for protected planning plus registered BUILD / TEST / VERIFY execution. It deliberately stops at IMPLEMENT when real implementation evidence is required and at REVIEW when independent review authority is required. It does not grant autonomous source editing, arbitrary shell access, Work Specification self-approval, Git commit/push/merge, Vercel production promotion, or production deployment authority.

## v0.13.0 implementation outcome

The candidate now includes:

- a protected `AutonomyCoordinator` bound to the existing Engineering Run state machine and optimistic run revisions;
- an isolated Vercel Sandbox executor using deployment-scoped Vercel identity;
- non-persistent sandboxes with deny-all network policy and no forwarded application environment or product secrets;
- a server-owned protected command registry for BUILD, TEST, and VERIFY;
- repository-backed sandbox initialization for protected execution stages;
- bounded observable execution evidence including invocation/output digests, exit status, duration, bounded excerpts, timeout/redaction state, executor identity, and network policy identity;
- deterministic protected PLAN evidence derived from the immutable server-owned acceptance map;
- executor preflight before PLAN mutation;
- fail-closed `EXECUTOR_UNAVAILABLE` behavior that leaves a recoverable PLAN run and revision unchanged;
- durable protected failure behavior for BUILD / TEST / VERIFY failures;
- explicit stop reasons for IMPLEMENT, REVIEW, PAUSED, FAILED, COMPLETE, CANCELLED, SPEC_AMENDMENT, executor unavailability, execution failure, and maximum bounded steps;
- a compact accessible `Run autonomously` control on eligible Code stages;
- visible autonomy stop-state feedback without allowing the client to mutate durable backend authority fields;
- browser acceptance coverage for the autonomy control, safe executor-unavailable behavior, unchanged PLAN state, and reduced-graphics parity;
- v0.13 API/client release metadata and default active product-spec identity.

No new database table or migration is required. Existing Engineering Run / attempt persistence remains the evidence store.

## Preview topology and routing

The candidate uses the existing two-project Vercel topology:

1. Web project `parallax`.
2. API project `parallax-api`.

The bounded Sandbox is runtime execution infrastructure used by the API, not a third application deployment.

Preview web deployment:

- deployment: `dpl_288XuPaFzCHHjS7tYdzEV7H9bPT4`;
- unique URL: `https://parallax-9iqolf056-lew7.vercel.app`;
- Git commit: `7f5178cec5cac755ff15e8369629e6127bff57e8`;
- state: `READY`;
- branch alias: `https://parallax-git-p2-v0130-bounded-autonomy-lew7.vercel.app`.

Preview API deployment carrying the latest API-affecting candidate state:

- deployment: `dpl_tCFVW4WreM8fBvT6nkiC1U8Mm5Nu`;
- unique URL: `https://parallax-qvtn2fey8-lew7.vercel.app`;
- Git commit: `0e6302ea1180b7fa085f3740ab906420033d7dae`;
- state: `READY`;
- branch alias: `https://parallax-api-git-p2-v0130-bounded-autonomy-lew7.vercel.app`.

The later candidate commit changes only web preview routing, so the API project correctly does not need a newer successful application build for that change.

The web configuration now routes `/p2-api/*` on the bounded-autonomy **branch alias only** to the bounded-autonomy API branch alias. All other web hosts retain the existing production API fallback. This fixes the prior test flaw where a preview web client would otherwise exercise the production API instead of the v0.13 API candidate.

Vercel preview authentication and the cross-project preview rewrite still require interactive operator verification. Vercel reports both relevant deployments as READY, but the automated connector cannot complete the browser SSO/cookie flow required to prove the protected preview end-to-end.

## Exact-head validation evidence

Candidate head `7f5178cec5cac755ff15e8369629e6127bff57e8` passed both exact-head workflows.

### Bounded Autonomy Pilot

GitHub Actions run `32556123923` completed **SUCCESS**.

Passed gates:

- approved `P2-V0.13.0` specification validation;
- API dependency installation and Python compilation;
- protected execution/autonomy test subset;
- full API regression suite;
- client dependency installation;
- TypeScript typecheck;
- response-state tests;
- Expo web export.

### Parallax P2 release CI

GitHub Actions run `32556123942` completed **SUCCESS**.

Passed gates:

- Fast API + contract checks;
- full API tests;
- Fast client checks;
- TypeScript and response-state tests;
- Expo web build;
- dependency-audit evidence capture;
- Playwright browser / Skia acceptance, including the v0.13 Code/autonomy stop-state browser scenario;
- protected Engineering / Reason / Code promotion evaluation and regression-rejection checks;
- existing DSPy release-compilation safety gate.

The inherited general release workflow still names its DSPy compile/verification target as `P2-V0.12.0`; therefore this record does **not** claim a DSPy-compiled v0.13 plan. v0.13 itself is validated by the dedicated exact-head bounded-autonomy specification and implementation workflow. Aligning the shared release workflow to the next production spec remains a release-hardening task before production promotion.

## Failure-safety state

The validated behavior is intentionally fail closed:

- executor unavailable during PLAN preflight → return `EXECUTOR_UNAVAILABLE`; preserve PLAN and its revision;
- stale caller revision → reject rather than silently retarget;
- missing/extra/duplicated acceptance coverage → protected validator rejects the stage;
- BUILD / TEST / VERIFY command failure or timeout → record failed protected evidence and stop;
- IMPLEMENT → stop and require real implementation evidence rather than fabricate artifacts;
- REVIEW → stop and require independent review authority;
- PAUSED / FAILED / CANCELLED / SPEC_AMENDMENT → no silent autonomous continuation;
- application/provider secrets are not forwarded into the sandbox;
- client/model input cannot supply executable command strings.

## Operator preview test required

The remaining release question is whether the real protected Vercel preview can create and execute the isolated Sandbox under the API preview's deployment identity and whether the web branch alias can reach the protected API branch alias through the cross-project preview route.

Expected first interactive path:

1. Open the bounded-autonomy web branch preview and complete Vercel/Parallax sign-in if requested.
2. Start a fresh Code conversation.
3. Capture and approve its Work Specification.
4. Confirm the Code run is `PLAN`, bound to the approved revision, and shows `Run autonomously`.
5. Invoke `Run autonomously`.
6. If Sandbox is available, the executor preflight passes and protected PLAN advances to `IMPLEMENT`, where Parallax intentionally stops with `IMPLEMENTATION_REQUIRED`.
7. If Sandbox identity/provider access is unavailable, Parallax must remain at `PLAN` and show `Autonomy stopped · isolated executor unavailable; no plan state was changed`.

A fresh UI-driven pilot does not progress beyond IMPLEMENT because v0.13 intentionally lacks autonomous source-editing authority and refuses to fabricate implementation evidence. BUILD / TEST / VERIFY autonomous execution is covered by protected automated tests and becomes available only when valid implementation evidence exists.

## Deployment state vocabulary

For v0.13.0 candidate:

- Specification approved: **YES**
- Implemented: **YES**
- Exact-head bounded-autonomy workflow: **PASS**
- Exact-head API regression suite: **PASS**
- Exact-head client typecheck/export: **PASS**
- Browser / Skia acceptance: **PASS**
- Bounded-autonomy browser stop-state acceptance: **PASS**
- Protected Engineering / Reason / Code evaluation: **PASS**
- Shared inherited DSPy release gate: **PASS — still targets v0.12.0**
- Preview web deployment READY: **YES**
- Preview API deployment READY: **YES**
- Preview branch web → preview branch API routing configured: **YES**
- Interactive protected cross-project preview routing verified: **PENDING**
- Live Vercel Sandbox preflight verified by operator: **PENDING**
- Merged to `main`: **NO**
- Production promoted: **NO**
- v0.13.0 deployment-verified: **NO — preview operator test pending**
- Production v0.12.0 remains deployment-verified: **YES**

## Current product baseline

Production remains v0.12.0, including conversation-first Reason, durable approved Work Specifications, immutable approved-spec Code binding, Editorial Optical conversation material, Ambient Chroma Flow, optical response inscription, mobile governed-surface discipline, same-origin hosted-web resilience, and Google identity with server-owned authorization.

The v0.13 preview extends that baseline with a bounded execution plane rather than replacing those capabilities.

## Governance status

- `CURRENT-STATE.md`: advanced to the v0.13.0 validated-preview candidate, exact-head CI evidence, Vercel preview evidence, production separation, and remaining operator verification boundary.
- `ARCHITECTURE.md`: advanced to v2.1 because v0.13.0 adds a durable bounded-autonomy coordinator, protected command registry, and Vercel Sandbox execution plane/trust boundary.
- `DESIGN-SYSTEM.md`: unchanged; the new control and stop-state treatment remain within the established conversation-native visual language and do not establish a new durable design rule.
- `PROJECT-CONSTITUTION.md`: unchanged; authority, human-control, evidence, safety, and release principles remain consistent with the existing constitution.

Historical release evidence remains preserved in repository history.
