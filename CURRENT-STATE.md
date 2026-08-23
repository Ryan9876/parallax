# Parallax 2.0 Current State

Release: App-builder Wave 1 foundation
Date: 2026-08-22
Status: DEPLOYED — PRODUCTION VERIFIED FOUNDATION; END-TO-END APP BUILDING NOT YET COMPLETE
Production branch: `main`
Production application commit: `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` (unchanged v0.13.9 client)
Production API deployment: `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB`

## Current production baseline

Parallax now has the first deployed app-builder foundation while preserving the v0.13.9 conversation/client experience.

The existing production Code path still provides durable Work Specifications, immutable approved-spec Engineering Run binding, protected Code stages, bounded autonomy, Vercel Sandbox execution for registered commands, protected evaluation, Google authorization, durable persistence, and explicit human authority boundaries.

Wave 1 adds four durable backend foundations:

1. **Canonical Project/App lifecycle — P2-V0.14.1**
   - server-generated UUID Project identity;
   - owner-scoped create/list/read persistence and API;
   - immutable opaque `workspace_ref = project:<id>` identity;
   - optional bounded repository identity metadata;
   - additive production `projects` table with RLS enabled and direct `anon` / `authenticated` access revoked.

2. **Safe source implementation and patch engine — P2-V0.14.2**
   - bounded text source mutation inside an explicit isolated filesystem root;
   - exact expected-base digest protection and commit-time pre-image recheck;
   - traversal/symlink, binary, secret-sensitive, malformed, stale, oversized, unsupported and no-op patch rejection;
   - atomic multi-file prepare/apply/rollback behavior;
   - deterministic before/after/diff/artifact evidence;
   - explicit `protected_stage_authority: false`, with no shell, Git, network or deployment authority.

3. **Project-scoped tool authority contracts — P2-V0.14.3**
   - immutable capability/action/request/approval/decision/result/audit contracts;
   - server-owned fail-closed capability and approval registries;
   - exact project/tool/action matching;
   - destructive-action human approval invariant;
   - reserved denial of generic shell/exec/command/subprocess/raw-HTTP/network escape hatches;
   - structurally distinct `DENIED`, `FAILED` and `SUCCEEDED` outcomes;
   - no concrete provider adapter or credential exposure in this foundation.

4. **App-builder evaluation and observability spine — P2-V0.14.4**
   - versioned development and promotion suites;
   - deterministic protected scoring and critical-failure semantics;
   - coverage for project isolation, specification binding, implementation evidence, BUILD/TEST/VERIFY truthfulness, tool authority, interruption/recovery and evidence hygiene;
   - fail-closed secret and hidden-reasoning rejection;
   - digest-based observable evidence rather than raw provider payloads.

## Wave 1 integration and validation

The four worker candidates were not merged directly to production. They were serialized through `integration/wave1-app-builder` and revalidated cumulatively.

Final integration candidate:

- PR `#57` — **Wave 1 app-builder integration candidate**;
- validated head `345c6bc65faa9356c6035eb50bef6734bb7a6614`;
- production merge commit `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`.

Exact final cumulative validation:

- `Parallax Workstream Spec Validation` run `32603877967` — **SUCCESS**;
- `Parallax P2 CI` run `32603877968` — **SUCCESS**;
- `Bounded Autonomy Pilot` run `32603877972` — **SUCCESS**.

The integration branch was also revalidated after #44 and after #45 before the next interacting workstream was added. This prevents isolated worker success from being treated as proof that the combined runtime is safe.

The workstream spec gate now deterministically validates each changed semantic specification against its committed DSPy-generated compiled plan and protected acceptance map. Weak stochastic local-model regeneration is no longer used as a per-PR promotion oracle; the existing release DSPy lane remains the repository-level compiler-execution proof.

## Production deployment verification

### API

Vercel production deployment `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB` is `READY`, targets production, and carries exact main commit `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`.

Production aliases include:

- `parallax-api-tan.vercel.app`;
- `parallax-api-lew7.vercel.app`;
- `parallax-api-git-main-lew7.vercel.app`.

Live checks after deployment:

- `GET /health` → HTTP 200, service `parallax-api`, status `ok`;
- `GET /ready` → HTTP 200, database `ok`;
- unauthenticated `GET /v1/projects` → HTTP 401 with `Authentication required`, confirming the new Project surface remains behind the existing private authentication boundary;
- Vercel runtime error clusters for the API over the verification window: none observed.

### Database

The additive Project migration was applied before code promotion. Production verification confirms the `projects` table exists, has the expected schema, RLS is enabled, and direct client-role table access remains revoked. FastAPI remains the application authorization boundary.

### Web

Wave 1 contains no client implementation change. The Vercel web build for the main merge was canceled by the repository's path-aware deployment rules as intended. The deployed web application therefore remains the previously verified v0.13.9 client at `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` rather than creating a redundant production web build.

## Canonical Project identity rules

`Project.id` is now the canonical durable application identity.

`workspace_ref` is an opaque identity seam only. It is **not** a filesystem path and must never be interpreted as one by callers, models, tools or provider adapters.

`repository_ref` is bounded repository identity metadata only. It grants no Git, network, connector or deployment authority.

Tool authority must bind to the canonical Project ID after owner-scoped Project resolution. Filesystem execution must resolve through a protected Project-to-workspace allocator rather than a caller-selected path.

## What is not yet complete

Wave 1 deliberately establishes safe primitives and contracts rather than claiming an end-to-end autonomous app builder.

The current critical path is:

1. bind conversations, Work Specifications and Engineering Runs to the canonical Project identity;
2. implement a protected Project-to-isolated-workspace allocator;
3. connect the safe patch engine to the protected IMPLEMENT stage without treating patch success as stage authority by itself;
4. preserve one implementation workspace/revision across IMPLEMENT → BUILD → TEST → VERIFY instead of creating unrelated fresh sandboxes per stage;
5. adapt tool-authority contracts to concrete narrowly scoped GitHub/Vercel actions without generic shell/HTTP authority;
6. map implementation/tool/runtime evidence into the app-builder evaluation spine and add app-builder protected promotion gates;
7. prove interruption, retry, idempotency and resume behavior across project-scoped runs;
8. add the minimal project/diff/preview/review UX only after the backend contracts stabilize.

Until these are complete, Parallax should not claim it can autonomously build arbitrary applications end to end.

## Current operator-visible client baseline

The production web/client remains v0.13.9 and preserves:

- transparent glossy 3D interlocking-knot identity;
- Ambient Chroma Flow;
- rounded translucent Work Specification material;
- stream-synchronized optical engraving treatment;
- response live-edge following with intentional scroll-away preservation;
- mobile/iOS keyboard-safe in-flow composer geometry;
- Code/Engineering Run status and bounded-autonomy controls.

The previously pending real-device live-edge composition check and first real operator Sandbox exercise remain useful operator verification items, but they do not block the verified Wave 1 backend foundation.

## Parallel ChatGPT development state

The GitHub-authoritative parallel-development model is active under `PROJECT-CONSTITUTION.md` v1.3 and `PARALLEL-DEVELOPMENT.md`.

Wave 1 demonstrated the intended model in practice:

- four worker chats operated on isolated workstreams #43–#46;
- worker ownership remained bounded;
- workers prepared validated PRs without production merge/deploy authority;
- Integration / Control Tower serialized the interacting candidates;
- the cumulative integration branch was revalidated before production promotion;
- a CI design defect discovered during parallel work was corrected through #54 / PR #55 before promotion.

Issues #43–#46 are complete. Issue #32 remains the app-builder program record and now advances to Wave 2 integration work.

## Approved Wave 3 completion contract

Material decisions recorded 2026-08-22: Wave 3 is required to operate as an end-to-end **bounded autonomous app-building and validation loop**, not as a one-pass implementation stage, and it must materially reduce development cycle time rather than merely automate the existing serial process.

Planned Wave 3 flow:

`approved objective/spec → PLAN → typed implementation proposal → protected mutation → same-lineage BUILD/TEST/VERIFY → browser exercise → deterministic DOM/accessibility/console/network validation → screenshot capture → screenshot regression + multimodal computer-vision review → autonomous correction/retry → bounded Git/preview delivery → protected evaluation → operator review`

Wave 3 must continue autonomously until either:

1. all protected functional, visual, security, lineage and acceptance gates pass and the result is preview-ready for operator review;
2. a defined human-control boundary is reached, including production merge/promotion, destructive or privileged actions, required approval, missing authorization/credential, material specification ambiguity or an unrecoverable bounded failure; or
3. an explicit retry, step, cumulative-churn, runtime or resource bound is reached, in which case Parallax must stop with actionable evidence rather than loop indefinitely.

Visual QA is therefore a Wave 3 requirement. Deterministic browser/layout/accessibility failures remain authoritative; multimodal vision may detect semantic visual defects but cannot override deterministic failures. The loop must preserve a last-known-good candidate and reject autonomous corrections that introduce protected regressions.

Wave 3 development acceleration is also an approved requirement. The planned architecture must include:

- continuous bounded worker utilization when safe independent work exists;
- a fast CI lane for compile/focused tests/contracts/typecheck/changed-area validation and a separate expensive promotion lane for worker completion, integration milestones and release candidates;
- machine-checkable cross-workstream interface contracts so Project/lineage/runtime/provider/evidence mismatches are found before late integration;
- permanent representative reference-app harnesses for repeated end-to-end development and regression exercises;
- safe dependency/browser/build/baseline/artifact caching where reuse cannot weaken exact-head or source-lineage evidence;
- automated Integration / Control Tower composition that detects integration-ready candidates, orders dependencies, composes them, runs cumulative gates and identifies interface failures;
- automatic conversion of reproducible integration/test failures into bounded corrective work with attached evidence.

Automatic worker stall detection and recovery is now also an approved Wave 3 requirement. The planned architecture must include:

- bounded worker leases and meaningful-progress heartbeats based on durable state changes, not merely status text or model activity;
- explicit worker lifecycle states including `STALLED`, `RECOVERING`, `REASSIGNED`, `HUMAN_REQUIRED` and `READY_FOR_INTEGRATION`;
- durable resumable checkpoints preserving canonical Project/run identity, approved Work Spec/compiled-plan reference, accepted source lineage, current step, retry state, last-known-good candidate, normalized evidence and outstanding blockers/dependencies;
- watchdog classification of stalls such as agent/process loss, CI/test hangs, provider outages, dependency waits, rate limits, credentials/authorization, contention/deadlock and repeated implementation failure;
- automatic bounded retry, checkpoint resume or reassignment before operator escalation when recovery is safe;
- single-writer lease semantics so a stale worker fails closed after lease loss and cannot race a recovered/reassigned worker;
- no-progress/oscillation detection and bounded retry/backoff so recovery cannot become an infinite compute loop;
- Control Tower visibility into worker health, last meaningful progress, checkpoint/source-lineage identity, retries, stall cause and next recovery action;
- a protected promotion test that deliberately kills or stalls a worker/process and proves another execution resumes from the durable checkpoint without lost accepted work, duplicate mutation, lineage corruption or a manual operator `resume` command.

The target operating model is continuous: workers produce candidates while the integration controller continuously composes and validates them, with full expensive promotion gates reserved for meaningful boundaries rather than every small edit. Ordinary worker stalls should be detected, recovered or reassigned automatically instead of waiting for the operator to notice and restart them.

### Platform-wide inheritance decision

The Wave 3 development baseline is now a platform policy for **every Project Parallax develops**, not special behavior reserved for development of Parallax itself.

The durable policy stack is:

`Parallax platform baseline → Project profile → approved Work Specification → capability-specific validation plan`

The strictest applicable requirement wins. Project profiles and Work Specifications may add stricter constraints, but they may not silently weaken the platform baseline for canonical identity, specification binding, source lineage, tool/mutation authority, durable checkpoints, bounded autonomy, worker-stall recovery, evidence integrity, rollback, protected promotion, or human-control boundaries.

Validation remains capability-aware rather than blindly identical across projects. Web/mobile projects can require browser flows, layout/accessibility checks, screenshot regression and multimodal visual QA; APIs can require schema/contract/auth/integration/reliability/performance checks; CLIs can require command/workflow/exit-code/output checks. Unsupported required validation must fail closed or require an explicit approved exception rather than being silently skipped.

### Universal Wave 3 optimization decision

The Wave 3 efficiency architecture now applies identically to **how Parallax is built** and **how Parallax builds every Project**. It is an inherited platform requirement rather than a one-off optimization for the Parallax repository.

Wave 3 must implement:

1. **critical-path scheduling and bounded work stealing** so worker capacity reduces time to the validated objective rather than merely maximizing worker occupancy;
2. **change-impact-driven fast validation** using a machine-readable file/component/service/contract/test impact graph, while full protected promotion suites remain mandatory at worker-completion/integration/release boundaries;
3. **immutable secret-free warm execution environments** keyed by toolchain/lock/configuration digests so workers avoid repeated environment setup without confusing caches with authoritative source state;
4. **validated pattern/component/configuration reuse** whose artifacts are revalidated against the current Project rather than trusted because they worked previously;
5. **privacy-safe failure fingerprinting and repair memory** that can propose proven repairs without transferring private Project source/secrets into global memory or bypassing protected mutation/validation;
6. **adaptive model routing** to reduce latency/cost for routine work while escalating difficult tasks and keeping protected evaluation/authority independent of the generating model;
7. **specification preflight** for contradictions, missing dependencies, impossible/untestable acceptance criteria, unsupported validation, authority conflicts and high-consequence ambiguity before implementation starts;
8. **speculative integration** of immutable worker checkpoints on disposable candidates so interface drift is detected early without advancing accepted lineage, merge state or release authority;
9. **automatic workstream sizing/rebalancing** so work is large enough to be useful but small enough to recover, validate and integrate without unnecessary fragmentation;
10. **development-performance telemetry** for planning, generation, environment preparation, build, validation, provider waits, retries, integration, stall recovery and human waits using bounded non-secret evidence.

Optimization must remain subordinate to correctness: impact analysis cannot waive promotion checks; warm environments/caches require provenance; speculative integration is non-authoritative; adaptive routing cannot lower protected standards; work stealing cannot violate leases/path ownership; and cross-Project reuse/telemetry cannot become a data-exfiltration path.

This universal optimization contract is now durable governance/architecture in `PROJECT-CONSTITUTION.md` v1.3 and `ARCHITECTURE.md` v2.4. Runtime enforcement remains a **Wave 3 requirement / not yet implemented**.

These Wave 3 runtime capabilities remain approved roadmap/exit-condition decisions only. They are **not yet implemented, validated, merged, deployed or deployment-verified**.

## Deployment state vocabulary

- v0.13.9 client baseline: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Wave 1 Project lifecycle foundation: **VALIDATED / MERGED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Wave 1 safe patch engine: **VALIDATED / MERGED / DEPLOYED AS FOUNDATION**
- Wave 1 tool-authority contracts: **VALIDATED / MERGED / DEPLOYED AS FOUNDATION**
- Wave 1 app-builder evaluation spine: **VALIDATED / MERGED / DEPLOYED AS FOUNDATION**
- production Project migration: **APPLIED / VERIFIED**
- production API deployment: **READY / HEALTH 200 / READY 200 / NO ERROR CLUSTERS OBSERVED**
- new Project API authentication boundary: **FAIL-CLOSED / UNAUTH 401 VERIFIED**
- complete project-scoped IMPLEMENT runtime: **NOT YET INTEGRATED**
- concrete GitHub/Vercel app-builder provider actions: **NOT YET INTEGRATED**
- end-to-end app-building loop: **NOT YET DEMONSTRATED**
- Wave 3 autonomous visual QA and correction loop: **APPROVED ROADMAP REQUIREMENT / NOT YET IMPLEMENTED**
- Wave 3 accelerated continuous worker/integration architecture: **APPROVED ROADMAP REQUIREMENT / NOT YET IMPLEMENTED**
- Wave 3 automatic worker stall detection/recovery/reassignment: **APPROVED ROADMAP REQUIREMENT / NOT YET IMPLEMENTED**
- inherited development-policy governance: **IMPLEMENTED IN AUTHORITATIVE POLICY / RUNTIME ENFORCEMENT PENDING WAVE 3**
- universal Wave 3 optimization governance: **IMPLEMENTED IN AUTHORITATIVE POLICY / RUNTIME ENFORCEMENT PENDING WAVE 3**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the deployed Wave 1 foundation and the approved Wave 3 autonomous/acceleration/stall-recovery/platform-inheritance/universal-optimization decisions.
- `ARCHITECTURE.md`: updated to v2.4 with inherited policy plus universal critical-path, impact-testing, warm-environment, reuse/repair-memory, adaptive-routing, preflight, speculative-integration, workstream-sizing and telemetry architecture; this does not claim runtime enforcement already exists.
- `PROJECT-CONSTITUTION.md`: updated to v1.3 so both Parallax self-development and every Parallax-developed Project inherit the non-weakenable development-efficiency baseline.
- `DESIGN-SYSTEM.md`: unchanged; this policy/architecture decision introduces no implemented visual or interaction-system change.

Historical release, CI, workstream, preview and deployment evidence remains preserved in GitHub Actions, GitHub issues/PRs and Vercel history.
