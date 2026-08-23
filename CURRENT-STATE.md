# Parallax 2.0 Current State

Release: App-builder Wave 1 production foundation + Wave 2 validated integration candidate
Date: 2026-08-23
Status: **PRODUCTION = WAVE 1 DEPLOYMENT-VERIFIED; WAVE 2 = INTEGRATION-COMPLETE / READY FOR PRODUCTION-ROLLOUT PREPARATION / NOT MERGED / NOT DEPLOYED**

## Production truth

Production remains the verified Wave 1 app-builder foundation. Wave 2 has not been merged to `main`, its new migrations have not been applied, production source-lineage storage/provider credentials have not been provisioned, and no Wave 2 production deployment has occurred.

- production application deployment commit: `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`
- production web: v0.13.9 / deployment `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy`
- production API: deployment `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB`
- production API `/health`: verified 200
- production API `/ready`: verified 200 / database ok
- unauthenticated `/v1/projects`: verified 401
- Wave 1 Project migration: applied and verified with RLS/direct-client-role restrictions preserved

## Authoritative governance

- `PROJECT-CONSTITUTION.md` v1.3
- `ARCHITECTURE.md` v2.4
- `DESIGN-SYSTEM.md` v2.1
- `CURRENT-STATE.md` — this snapshot
- concurrent-development protocol: `PARALLEL-DEVELOPMENT.md`

GitHub issues/PRs/workflows and deployment evidence are authoritative for active implementation/release state when chat recollection differs.

## Wave 2 integration exit

Cumulative PR: `#67` — **Wave 2 app-builder integration candidate**
Branch: `integration/wave2-app-builder`
Final validated head: `d4ca9c95527198c7884f87056afab8bbcc85ab39`
PR state: **READY FOR REVIEW / MERGEABLE / NOT MERGED TO MAIN**

Wave 2 now serializes the complete `P2-V0.15.1` through `P2-V0.15.10` app-builder tranche:

1. canonical Project/runtime identity and owner-scoped binding;
2. protected Project/run workspace and immutable source-lineage contract;
3. typed protected IMPLEMENT generation/mutation;
4. bounded GitHub/Vercel provider action contracts;
5. production-safe durable lineage with immutable private-object storage + transactional metadata/current-head CAS and disposable local materialization only;
6. actual engineering-run runtime composition with exact-lineage Vercel Sandbox BUILD/TEST/VERIFY and no fresh-repository fallback after accepted IMPLEMENT;
7. concrete bounded GitHub REST and Vercel Preview clients with scoped/short-lived credential contracts and secret-safe failures;
8. minimum Project select/create client compatibility for canonical `project_id` Code conversations;
9. first-run repository bootstrap plus exact verified-lineage GitHub branch/commit/PR and Vercel Preview delivery, with bounded provider action/audit persistence and replay after process recreation without duplicate provider mutation;
10. #46 app-builder evaluation evidence derived from persisted Project/spec/run/lineage/stage/provider audit facts plus a protected restart/reference-app proof.

Issues #59–#62, #68–#71, #79 and #80 are complete at the Wave 2 integration boundary.

## Final Wave 2 proof

The validated candidate proves at repository/integration-test level:

`Project selection/binding → approved Work Specification → PLAN → repository bootstrap → typed implementation proposal → safe mutation → durable accepted lineage → exact-lineage BUILD/TEST/VERIFY → bounded GitHub publication → Vercel Preview → unchanged #46 protected evaluation from persisted runtime/provider evidence → operator REVIEW`

The reference proof recreates runtime/request composition between meaningful stages, reconstructs accepted source from durable lineage, replays IMPLEMENT without duplicate source mutation, resolves the accepted provider delivery after recreation, and replays publication without duplicate commit/PR/Preview mutation. Negative Project/spec/digest/lineage/stage/provider/preview/evidence/authority cases fail closed. Preview remains the autonomous provider ceiling and #46 scoring/critical-failure semantics are unchanged.

The final #79→#80 integration uses a read-only evidence bridge over #79's durable Engineering Attempt delivery record. Evaluation does not rerun provider mutations and does not introduce a second provider-audit persistence system.

## Final cumulative validation

At exact integration head `d4ca9c95527198c7884f87056afab8bbcc85ab39`:

- Parallax Workstream Spec Validation `32620881155` — **SUCCESS**
- Parallax P2 CI `32620881130` — **SUCCESS**
- Bounded Autonomy Pilot `32620881096` — **SUCCESS**
- Vercel Git Preview check — web **SUCCESS**
- Vercel Git Preview check — API **SUCCESS**

The final PR #67 diff contains no temporary worker-validation workflow. Integration-only test defects discovered during serialization were corrected without weakening runtime semantics or protected acceptance requirements.

## Wave 2 production-rollout boundary

Wave 2 development/integration is complete, but production readiness is not yet deployment-verified. Before production promotion, Control Tower/operator must separately prove or configure, as applicable:

- readiness/application of `20260822_0007_project_runtime_binding.sql`;
- readiness/application of `20260823_0008_durable_source_lineage.sql`;
- private durable object storage configuration for accepted source contents;
- approved scoped/short-lived GitHub and Vercel credential issuers for the concrete provider clients;
- disposable live least-privilege repository + Preview verification;
- exact-head release validation after any rollout-preparation change;
- controlled merge to `main` and production deployment;
- post-deploy `/health`, `/ready`, authentication, migration, source-lineage/runtime/provider behavior and error-observability verification;
- rollback and recovery readiness.

None of those production steps is recorded as complete until evidenced. PR #67 must not be described as deployed merely because its Vercel Git Preview checks are green.

## Approved Wave 3 platform contract

Wave 3 implementation begins after the Wave 2 release is safely promoted and deployment-verified. Its target is an end-to-end bounded autonomous development system that continues from approved objective through implementation, validation and correction until protected criteria pass or a defined human/resource boundary is reached.

Wave 3 requirements already approved as durable governance/architecture include:

- browser/workflow execution, deterministic DOM/accessibility/console/network validation, screenshot regression and multimodal visual QA, with deterministic failures authoritative;
- autonomous diagnose/correct/retest loops with last-known-good preservation, retry/churn/runtime budgets and oscillation/no-progress detection;
- durable worker checkpoints, leases/meaningful-progress heartbeats, `STALLED`/`RECOVERING`/`REASSIGNED`/`HUMAN_REQUIRED` states, single-writer recovery and a deliberate worker-kill/stall promotion proof;
- continuous bounded worker utilization, fast-vs-promotion CI, machine-checkable cross-workstream contracts, permanent reference apps, safe caching, automated Control Tower composition and evidence-backed corrective-work dispatch;
- critical-path scheduling/work stealing, change-impact testing, warm secret-free environments, validated reusable patterns/components/configuration, privacy-safe failure/repair memory, adaptive model routing, spec preflight, speculative integration, automatic workstream sizing/rebalancing and development-performance telemetry.

The same Wave 3 baseline governs development of Parallax and every Project Parallax develops through:

`Parallax platform baseline → Project profile → approved Work Specification → capability-specific validation plan`

Projects may strengthen but may not silently weaken the platform baseline. Wave 3 runtime enforcement remains **APPROVED / NOT YET IMPLEMENTED / NOT DEPLOYED**.

## Deployment-state vocabulary

- Wave 1 production foundation: **VALIDATED / MERGED / DEPLOYED / DEPLOYMENT-VERIFIED**
- production client: **v0.13.9 / DEPLOYED / VERIFIED**
- Wave 2 P2-V0.15.1–P2-V0.15.10: **VALIDATED / INTEGRATION-COMPLETE / READY FOR PRODUCTION-ROLLOUT PREPARATION / NOT MERGED TO MAIN / NOT DEPLOYED**
- Wave 2 migrations/storage: **CODE VALIDATED / PRODUCTION NOT APPLIED OR PROVISIONED**
- Wave 2 provider clients: **CODE VALIDATED / LIVE PRODUCTION CREDENTIAL BINDING NOT PROVISIONED OR VERIFIED**
- Wave 2 protected end-to-end reference loop: **DEMONSTRATED AT REPOSITORY/INTEGRATION-TEST LEVEL**
- Wave 3 inherited autonomous/optimization/stall-recovery policy: **AUTHORITATIVE GOVERNANCE / RUNTIME NOT YET IMPLEMENTED**

## Authoritative-record status

- `CURRENT-STATE.md`: updated for the final Wave 2 integration exit and production-rollout boundary.
- `ARCHITECTURE.md`: remains v2.4; update when the Wave 2 runtime is durably accepted into the merged/deployed architecture or another durable architectural decision changes.
- `PROJECT-CONSTITUTION.md`: remains v1.3; no governance authority boundary changed in this integration pass.
- `DESIGN-SYSTEM.md`: remains v2.1; no durable design-system rule changed.

Historical worker, integration, CI, preview and production evidence remains preserved in GitHub Actions, issues/PRs and Vercel history.
