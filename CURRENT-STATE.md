# Parallax 2.0 Current State

Release: App-builder Wave 1 production foundation + Wave 2 integration candidate
Date: 2026-08-22
Status: **PRODUCTION = WAVE 1 VERIFIED; WAVE 2 = VALIDATED THROUGH P2-V0.15.8 / NOT MERGED / NOT DEPLOYED / CLOSURE WORK ACTIVE**

## Production truth

Production remains the verified Wave 1 app-builder foundation. No Wave 2 runtime/client migration, storage provisioning, credential provisioning, merge, or production deployment has occurred.

- production branch: `main`
- production application commit: `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`
- production web: v0.13.9 client / deployment `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy`
- production API deployment: `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB`
- production API `/health`: verified 200
- production API `/ready`: verified 200 / database ok
- unauthenticated `/v1/projects`: verified 401
- production Project migration: applied and verified with RLS/direct-client-role restrictions preserved

Wave 1 production capabilities include canonical Project lifecycle, safe bounded source patching, project-scoped tool-authority contracts, protected app-builder evaluation/observability, approved-Work-Spec Code stages, bounded Vercel Sandbox execution, persistent conversations/specs/runs, authentication, and explicit human release authority.

## Authoritative governance

- `PROJECT-CONSTITUTION.md` v1.3
- `ARCHITECTURE.md` v2.4
- `DESIGN-SYSTEM.md` v2.1
- `CURRENT-STATE.md` — this snapshot
- concurrent-development protocol: `PARALLEL-DEVELOPMENT.md`

GitHub issues/PRs/workflows and deployment evidence are authoritative for active workstream/release state when chat recollection differs.

## Wave 2 integration candidate

Cumulative PR: `#67` — **Wave 2 app-builder integration candidate**
Branch: `integration/wave2-app-builder`
Current validated head: `a3c5d0f08c91f9407629df811aab6b28b8dde6ed`
PR state: **DRAFT / DO NOT MERGE / DO NOT DEPLOY**

### Integrated Wave 2 contracts

Initial tranche:

1. #59 / `P2-V0.15.1` — canonical Project/runtime binding
2. #60 / `P2-V0.15.2` — protected Project/run workspace and immutable source-lineage contract
3. #61 / `P2-V0.15.3` — protected IMPLEMENT runtime and typed implementation generation
4. #62 / `P2-V0.15.4` — bounded GitHub/Vercel provider-action contracts

Corrective tranche now serialized into the same cumulative candidate:

5. #68 / `P2-V0.15.5` — production-safe durable source lineage: immutable private object storage + transactional metadata/current-lineage CAS; local filesystem only for disposable materialization
6. #69 / `P2-V0.15.6` — actual engineering-run runtime composition with `ProtectedImplementationRuntime` and exact-lineage Vercel Sandbox BUILD/TEST/VERIFY; no fresh-repository fallback after accepted IMPLEMENT lineage
7. #70 / `P2-V0.15.7` — concrete bounded GitHub REST and Vercel Preview clients with scoped/short-lived credential contracts and secret-safe error normalization
8. #71 / `P2-V0.15.8` — minimum Project select/create compatibility and canonical `project_id` binding for new Code conversations while preserving Reason/historical behavior and existing client visual geometry

Issues #68–#71 are complete at the worker/integration-slice boundary. Worker PRs #72–#74 are closed/superseded by cumulative PR #67; #75 was merged into the integration branch.

### Cumulative validation

The first #68+#69 composition exposed one integration-only test defect: a helper named `test_allocator(root)` was accidentally collected by pytest. Control Tower renamed it to `make_test_allocator`; no runtime semantics changed. The repaired composition and every later cumulative head were revalidated before the next interacting slice was accepted.

#68 + #69 repaired head `27d78b49e4822c2192974e9ab7bbea8a39fad583`:

- Workstream Spec Validation `32614997434` — **SUCCESS**
- Parallax P2 CI `32614997438` — **SUCCESS**
- Bounded Autonomy Pilot `32614997302` — **SUCCESS**

After #70 at `1cf6f67a8958f6ab2941dc901dc2d8cfe2f1b0b9`:

- Workstream Spec Validation `32615124294` — **SUCCESS**
- Parallax P2 CI `32615124277` — **SUCCESS**
- Bounded Autonomy Pilot `32615124271` — **SUCCESS**

Final current #68–#71 head `a3c5d0f08c91f9407629df811aab6b28b8dde6ed`:

- Workstream Spec Validation `32615238613` — **SUCCESS**
- Parallax P2 CI `32615238611` — **SUCCESS**
- Bounded Autonomy Pilot `32615238604` — **SUCCESS**

The final current candidate therefore passes changed-spec/compiled-plan validation, full API regression, client typecheck/state/export, browser acceptance, protected promotion/regression evaluation, DSPy release compilation, and bounded-autonomy regression tests.

## What the validated Wave 2 candidate now proves

The unmerged candidate proves, at repository/integration-test level:

- new Code runtime identity binds to canonical owner-scoped `Project.id`;
- accepted implementation source has immutable durable lineage with reconstruction and stale-parent/CAS/idempotency protection;
- production-route autonomous composition can inject the protected IMPLEMENT runtime;
- BUILD/TEST/VERIFY reconstruct and execute the exact accepted lineage in deny-all Vercel Sandboxes instead of silently cloning unrelated fresh source;
- concrete GitHub/Vercel Preview clients preserve typed #62 action ceilings, canonical repository/source binding, idempotency and secret-safe failures;
- new client Code creation has the minimum Project selection/create compatibility required by the strict backend Project invariant;
- the existing protected CI/evaluation suites remain green after composition.

This is **validated integration-candidate evidence**, not production evidence.

## Remaining Wave 2 closure work

Wave 2 is not considered a usable end-to-end app builder yet. Operational-path review found two remaining composition/proof gaps.

### #79 — repository bootstrap and verified-source delivery composition

Issue: `#79`
Spec reservation: `P2-V0.15.9`
Branch: `ws/app-source-delivery-composition`

A brand-new strict run currently has no cumulative repository-backed first-lineage bootstrap path: #68 exposes `initialize(identity, SourceProvider)` while the #69 production runtime resolves an already-existing lineage. The normal runtime also does not yet carry the exact verified accepted lineage through concrete #70 GitHub branch/commit/PR and Vercel preview delivery before operator review.

#79 must close this using canonical owner-scoped Project repository binding, existing #45/#62 tool authority, durable #68 lineage, and #70 clients. Caller/model input must not select repository URLs, filesystem roots, credentials, generic transports, arbitrary Git commands, or production deployment targets. Retry/process recreation must remain idempotent. Preview remains the autonomous ceiling.

### #80 — real runtime evidence and restart/reference-loop proof

Issue: `#80`
Spec reservation: `P2-V0.15.10`
Branch: `ws/app-runtime-evidence-reference-loop`
Dependency: final #79 contract; parallel protocol work is allowed but final readiness must reconcile to accepted #79.

#46 remains a strict recorded-evidence evaluator. #80 must derive its evidence from actual persisted Project/spec/run/lineage/stage/provider audit facts rather than hand-authored success fixtures, preserve #46 critical-failure semantics, and prove process recreation/retry without duplicate implementation mutation or provider publication.

Required reference loop:

`Project selection/binding → approved Work Spec → PLAN → repository bootstrap → typed proposal → safe patch → durable accepted lineage → exact-lineage BUILD/TEST/VERIFY → bounded Git publication → Vercel preview → protected #46 evaluation → operator REVIEW`

Deliberate wrong-Project/spec/lineage, stale-parent, false-evidence, provider-failure, interruption, duplicate-retry, missing-preview, secret-bearing-evidence and unrelated-source cases must be rejected.

Only after #79 + #80 are integrated and cumulatively green can Wave 2 be considered ready for production-rollout preparation.

## Production rollout boundaries still outstanding

Even after code closure, production promotion must separately prove/configure:

- migration `20260822_0007_project_runtime_binding.sql` readiness/application;
- migration `20260823_0008_durable_source_lineage.sql` readiness/application;
- private durable object storage configuration for accepted source contents;
- approved scoped/short-lived GitHub and Vercel credential issuers for the concrete provider clients;
- disposable live provider/Preview verification under least privilege;
- exact-head release gates and preview evidence;
- post-promotion `/health`, `/ready`, authentication, migration, runtime and error-observability verification;
- rollback/recovery readiness.

No such production step is recorded as complete until evidenced.

## Approved Wave 3 platform contract

Wave 3 begins only after the Wave 2 protected app-builder loop is closed. Its durable objective is a bounded autonomous development system that continues from approved objective through correction/validation until all protected criteria pass or a defined human/resource boundary is reached.

Required Wave 3 behavior includes:

- autonomous implement → build → test → browser exercise → deterministic DOM/accessibility/console/network checks → screenshot regression + multimodal visual QA → diagnose/correct/retest → bounded preview → protected evaluation;
- deterministic failures remain authoritative over model visual judgment;
- last-known-good preservation, retry/churn/runtime budgets and no-progress/oscillation detection;
- durable worker checkpoints, leases/heartbeats, explicit STALLED/RECOVERING/REASSIGNED/HUMAN_REQUIRED states, single-writer reassignment and automatic recovery without routine manual `resume`;
- fast-vs-promotion CI lanes, machine-checkable cross-workstream contracts, permanent reference-app harnesses, safe caching and automated Control Tower composition/failure dispatch;
- critical-path scheduling/work stealing, change-impact testing, warm secret-free environments, validated pattern/component/config reuse, privacy-safe failure/repair memory, adaptive model routing, specification preflight, speculative integration, automatic workstream sizing/rebalancing and development-performance telemetry;
- a deliberate worker-kill/stall promotion test proving another execution resumes from durable checkpoint without lost accepted work, duplicate mutation or lineage corruption.

The Wave 3 development baseline applies both to **development of Parallax itself** and to **every Project Parallax develops** through:

`Parallax platform baseline → Project profile → approved Work Specification → capability-specific validation plan`

The strictest applicable requirement wins. Projects may strengthen but may not silently weaken the platform baseline. Capability-specific validation adapts to web/mobile/API/CLI/etc. without disabling common identity, lineage, authority, recovery, evidence, rollback, privacy or human-control guarantees.

Wave 3 runtime enforcement is **approved architecture/governance only; not yet implemented or deployed**.

## Deployment-state vocabulary

- Wave 1 production foundation: **VALIDATED / MERGED / DEPLOYED / DEPLOYMENT-VERIFIED**
- production client: **v0.13.9 / DEPLOYED / VERIFIED**
- Wave 2 #59–#71 cumulative candidate: **VALIDATED / NOT MERGED TO MAIN / NOT DEPLOYED**
- durable source-lineage migration/storage for Wave 2: **CODE VALIDATED / PRODUCTION NOT APPLIED OR PROVISIONED**
- concrete provider clients: **CODE VALIDATED / LIVE PRODUCTION CREDENTIAL BINDING NOT PROVISIONED OR VERIFIED**
- Wave 2 end-to-end app-building loop: **NOT YET DEMONSTRATED — #79/#80 ACTIVE**
- Wave 3 inherited autonomous/optimization/stall-recovery policy: **AUTHORITATIVE GOVERNANCE / RUNTIME NOT YET IMPLEMENTED**

## Authoritative-record status

- `CURRENT-STATE.md`: updated for the validated #68–#71 cumulative candidate and explicit #79/#80 Wave 2 closure path while preserving Wave 1 as production truth.
- `ARCHITECTURE.md`: remains v2.4; no durable architecture change beyond the already-recorded inherited Wave 3 policy/optimization architecture is required by this integration status update.
- `PROJECT-CONSTITUTION.md`: remains v1.3.
- `DESIGN-SYSTEM.md`: remains v2.1; no design-system rule changed in this Control Tower integration pass.

Historical worker, integration, CI, preview and production evidence remains preserved in GitHub Actions, issues/PRs and Vercel history.