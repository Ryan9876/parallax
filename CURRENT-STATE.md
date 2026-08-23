# Parallax 2.0 Current State

Release: App-builder Wave 1 production foundation + Wave 2 final validated production candidate
Date: 2026-08-23
Status: **PRODUCTION = WAVE 1 DEPLOYMENT-VERIFIED; WAVE 2 = FINAL INTEGRATION VALIDATED / EXTERNAL VERCEL PREREQUISITES PENDING / NOT MERGED / NOT DEPLOYED**

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

## Wave 2 final integration candidate

Cumulative PR: `#67` — **Wave 2 app-builder integration candidate**
Branch: `integration/wave2-app-builder`
Final validated head: `00f7e73014d829a505bc4ef21ab2cc9e60c7c75c`
PR state: **READY FOR REVIEW / MERGEABLE / NOT MERGED TO MAIN**

Wave 2 now serializes the complete `P2-V0.15.1` through `P2-V0.15.12` app-builder tranche:

1. canonical Project/runtime identity and owner-scoped binding;
2. protected Project/run workspace and immutable source-lineage contract;
3. typed protected IMPLEMENT generation/mutation;
4. bounded GitHub/Vercel provider action contracts;
5. production-safe durable lineage with immutable private-object storage + transactional metadata/current-head CAS and disposable local materialization only;
6. actual engineering-run runtime composition with exact-lineage Vercel Sandbox BUILD/TEST/VERIFY and no fresh-repository fallback after accepted IMPLEMENT;
7. concrete bounded GitHub REST and Vercel Preview clients with scoped/short-lived credential contracts and secret-safe failures;
8. minimum Project select/create client compatibility for canonical `project_id` Code conversations;
9. first-run repository bootstrap plus exact verified-lineage GitHub branch/commit/PR and Vercel Preview delivery, with bounded provider action/audit persistence and replay after process recreation without duplicate provider mutation;
10. #46 app-builder evaluation evidence derived from persisted Project/spec/run/lineage/stage/provider audit facts plus a protected restart/reference-app proof;
11. live production-route source-delivery composition, exact server-owned target registration, short-lived GitHub Connect credential acquisition and durable lineage-table RLS/revoked-role hardening;
12. per-target production credential isolation so multiple canonical Projects can use distinct GitHub Connect connectors and Vercel Preview credentials without widening one request to another Project's provider target.

Issues #59–#62, #68–#71, #79, #80, #84 and #88 are complete at the Wave 2 integration boundary.

## Final Wave 2 proof

The validated candidate proves at repository/integration-test level:

`Project selection/binding → approved Work Specification → PLAN → repository bootstrap → typed implementation proposal → safe mutation → durable accepted lineage → exact-lineage BUILD/TEST/VERIFY → bounded GitHub publication → Vercel Preview → unchanged #46 protected evaluation from persisted runtime/provider evidence → operator REVIEW`

The reference proof recreates runtime/request composition between meaningful stages, reconstructs accepted source from durable lineage, replays IMPLEMENT without duplicate source mutation, resolves accepted provider delivery after recreation, and replays publication without duplicate commit/PR/Preview mutation. Negative Project/spec/digest/lineage/stage/provider/preview/evidence/authority cases fail closed. Preview remains the autonomous provider ceiling and #46 scoring/critical-failure semantics are unchanged.

Production composition additionally proves that canonical owner-scoped `Project.repository_ref` selects a server-owned target before credentials are resolved. Each target carries its own GitHub Connect connector reference and bounded Vercel token environment-variable reference. Only that selected Vercel secret is read, and the request-scoped Vercel credential provider/client receive a singleton target scope. A Vercel Connect GitHub token is accepted only after GitHub itself proves the installation token can access exactly the canonical repository.

The #79→#80 evidence bridge remains read-only over #79's durable Engineering Attempt delivery record. Evaluation does not rerun provider mutations and does not introduce a second provider-audit persistence system.

## Final cumulative validation

At exact integration head `00f7e73014d829a505bc4ef21ab2cc9e60c7c75c`:

- Parallax Workstream Spec Validation `32646469671` — **SUCCESS**
- Parallax P2 CI `32646469716` — **SUCCESS**, including full API, client/browser, production dependency audit, protected promotion evaluation and DSPy release compilation
- Bounded Autonomy Pilot `32646469680` — **SUCCESS**, including protected execution/autonomy, full API regression, client state/export
- Vercel API Preview `dpl_E1emBBqmS4jz4VbMeZC6sAcHPiLp` — **READY**, exact integration SHA
- Vercel runtime error check — **no error clusters observed**
- direct Preview `/health` probing is intercepted by Vercel Preview Authentication before application routing; this is access protection, not an application failure

P2-V0.15.11 authentic DSPy evidence: compiler run `32621606396` SUCCESS, artifact `9488544665`, digest `sha256:0013879518c00b28119ea951756f0b795badb5c0f86199191bdb548c315f85b9`.

P2-V0.15.12 authentic DSPy evidence: compiler run `32645066528` SUCCESS, artifact `9494664770`, digest `sha256:167d86a3e4ffba7907823a17f46b91658e4f93a8e554af503721743a30b538d9`.

## Wave 2 production-rollout boundary

Wave 2 code/integration is complete and exact-head validated, but production readiness is not deployment-verified. The remaining release blockers are external provisioning/evidence, not unimplemented app-builder code.

Before production promotion, Control Tower/operator must prove or configure:

- readiness/application of `20260822_0007_project_runtime_binding.sql`;
- readiness/application of `20260823_0008_durable_source_lineage.sql`;
- a **private Vercel Blob store** connected/authorized for `parallax-api`;
- because the accepted Python runtime uses `vercel>=0.9,<0.10`, Blob operations require `BLOB_READ_WRITE_TOKEN` (the Python Blob client does not currently inherit Vercel deployment OIDC for these operations);
- one repository-scoped **GitHub Vercel Connect connector** per registered repository target, attached to `parallax-api` for the intended environment(s);
- one dedicated project-scoped **Vercel Preview access credential** per registered Preview target, stored as a sensitive Vercel environment variable;
- `PARALLAX_VERCEL_PREVIEW_TARGETS_JSON` containing each exact repository/Vercel target plus its `github_connector` and bounded `vercel_token_env` reference;
- a disposable live least-privilege repository + Preview verification after those credentials are provisioned;
- controlled merge of PR #67 to `main` and production deployment only after prerequisite verification;
- post-deploy `/health`, `/ready`, authentication, migration, source-lineage/runtime/provider behavior and error-observability verification;
- rollback and recovery readiness.

`VERCEL_OIDC_TOKEN` is **not** a manual deployment secret. Vercel automatically injects and refreshes it on deployments, and the Wave 2 GitHub Connect adapter consumes that platform-provided token. Local development requires a pulled/generated development OIDC token, but production does not.

The currently connected Vercel action surface can verify projects, deployments and logs and can initiate deployments, but it does not expose Blob-store creation, Connect attachment or environment-variable mutation. No alternative installed management plugin providing those write capabilities was found. Therefore none of the external resources above is recorded as provisioned until separate Vercel provisioning evidence exists.

PR #67 must not be described as deployed merely because its Vercel Preview is green.

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
- Wave 2 P2-V0.15.1–P2-V0.15.12: **VALIDATED / INTEGRATION-COMPLETE / EXTERNAL PRODUCTION PREREQUISITES PENDING / NOT MERGED TO MAIN / NOT DEPLOYED**
- Wave 2 migrations/storage: **CODE VALIDATED / PRODUCTION NOT APPLIED OR PROVISIONED**
- Wave 2 provider clients/composition: **CODE VALIDATED / LIVE PRODUCTION CREDENTIAL BINDING NOT PROVISIONED OR VERIFIED**
- Wave 2 protected end-to-end reference loop: **DEMONSTRATED AT REPOSITORY/INTEGRATION-TEST LEVEL**
- Wave 3 inherited autonomous/optimization/stall-recovery policy: **AUTHORITATIVE GOVERNANCE / RUNTIME NOT YET IMPLEMENTED**

## Authoritative-record status

- `CURRENT-STATE.md`: updated for final `P2-V0.15.12` integration validation, exact Vercel Preview evidence and the corrected production prerequisite model.
- `ARCHITECTURE.md`: remains v2.4 because the Wave 2 runtime/composition is validated but has not yet been accepted into merged/deployed production architecture.
- `PROJECT-CONSTITUTION.md`: remains v1.3; no governance authority boundary changed in this release-preparation pass.
- `DESIGN-SYSTEM.md`: remains v2.1; no durable design-system rule changed.

Historical worker, integration, CI, preview and production evidence remains preserved in GitHub Actions, issues/PRs and Vercel history.
