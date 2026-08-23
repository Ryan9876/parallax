# Parallax 2.0 Current State

Release: App-builder Wave 1 production foundation + Wave 2 final validated production candidate
Date: 2026-08-23
Status: **PRODUCTION = WAVE 1 DEPLOYMENT-VERIFIED; WAVE 2 = FINAL INTEGRATION VALIDATED / RELEASE AUTHORIZED / VERCEL MANAGEMENT CREDENTIAL PENDING / NOT MERGED / NOT DEPLOYED**

## Production truth

Production remains the verified Wave 1 app-builder foundation. Wave 2 has not been merged to `main`, its new migrations have not been applied, production source-lineage storage/provider credentials have not been provisioned, and no Wave 2 production deployment has occurred.

Ops-only tooling/documentation commits have been merged to `main` and may trigger Vercel builds, but they do not constitute a Wave 2 application deployment.

- production application baseline commit: `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`
- production web baseline: v0.13.9 / deployment `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy`
- original deployment-verified Wave 1 API: `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB`
- later ops-only `main` deployment `dpl_HfHoqfGJkpPerbFXQuSTqz1Da7Gy`: READY at commit `f14a94dcf503e8ebd13e1f256f884bb86574300c`; this did not contain Wave 2 application changes
- Wave 1 API `/health`: verified 200
- Wave 1 API `/ready`: verified 200 / database ok
- unauthenticated `/v1/projects`: verified 401
- Wave 1 Project migration: applied and verified with RLS/direct-client-role restrictions preserved

## Authoritative governance

- `PROJECT-CONSTITUTION.md` v1.3
- `ARCHITECTURE.md` v2.4
- `DESIGN-SYSTEM.md` v2.1
- `CURRENT-STATE.md` — this snapshot
- concurrent-development protocol: `PARALLEL-DEVELOPMENT.md`

GitHub issues/PRs/workflows, Supabase migration/schema evidence, and Vercel deployment/runtime evidence are authoritative for active implementation/release state when chat recollection differs.

## Standing release authorization

On 2026-08-23 the operator explicitly authorized all remaining implementation/release work for the Wave 2 path, including reconciliation, prerequisite provisioning, production migration application, PR #67 merge, deployment, and post-deploy verification once protected prerequisites pass. This authorization is recorded in Control Tower issue #31 comment `5386856626`.

No additional approval is required for those already-authorized steps. Technical safety sequencing remains mandatory: production migrations, Wave 2 merge, and Wave 2 deployment must not occur until Vercel storage/provider credential prerequisites are successfully provisioned and verified.

## Wave 2 final integration candidate

Cumulative PR: `#67` — **Wave 2 app-builder integration candidate**
Branch: `integration/wave2-app-builder`
Validated application tree head: `00f7e73014d829a505bc4ef21ab2cc9e60c7c75c`
Current release-refresh head: `180943255e2a54f490c5f6375f559babd0e31454`
PR state: **READY / MERGEABLE / NOT MERGED TO MAIN**

`180943255...` is a tree-identical no-op commit over `00f7e730...`, created only to force GitHub to rebuild and revalidate the PR merge ref after ops/documentation changes landed on `main`. No Wave 2 application bytes changed; the application tree remains `e9598afa6dd2a6253d62e06f52b045c0503bdaa5`.

Wave 2 serializes the complete `P2-V0.15.1` through `P2-V0.15.12` app-builder tranche:

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
12. per-target production credential isolation so canonical Projects can use distinct GitHub Connect connectors and Vercel Preview credentials without widening one request to another Project's provider target.

Issues #59–#62, #68–#71, #79, #80, #84 and #88 are complete at the Wave 2 integration boundary.

## Final Wave 2 proof

The validated candidate proves at repository/integration-test level:

`Project selection/binding → approved Work Specification → PLAN → repository bootstrap → typed implementation proposal → safe mutation → durable accepted lineage → exact-lineage BUILD/TEST/VERIFY → bounded GitHub publication → Vercel Preview → unchanged #46 protected evaluation from persisted runtime/provider evidence → operator REVIEW`

The reference proof recreates runtime/request composition between meaningful stages, reconstructs accepted source from durable lineage, replays IMPLEMENT without duplicate source mutation, resolves accepted provider delivery after recreation, and replays publication without duplicate commit/PR/Preview mutation. Negative Project/spec/digest/lineage/stage/provider/preview/evidence/authority cases fail closed. Preview remains the autonomous provider ceiling and #46 scoring/critical-failure semantics are unchanged.

Production composition additionally proves that canonical owner-scoped `Project.repository_ref` selects a server-owned target before credentials are resolved. Each target carries its own GitHub Connect connector reference and bounded Vercel token environment-variable reference. Only that selected Vercel secret is read, and the request-scoped Vercel credential provider/client receive a singleton target scope. A Vercel Connect GitHub token is accepted only after GitHub proves the installation token can access exactly the canonical repository.

The #79→#80 evidence bridge remains read-only over #79's durable Engineering Attempt delivery record. Evaluation does not rerun provider mutations and does not introduce a second provider-audit persistence system.

## Final cumulative validation

Original exact application head `00f7e73014d829a505bc4ef21ab2cc9e60c7c75c`:

- Workstream Spec Validation `32646469671` — **SUCCESS**
- P2 CI `32646469716` — **SUCCESS**, including full API, client/browser, production dependency audit, protected promotion evaluation and DSPy release compilation
- Bounded Autonomy `32646469680` — **SUCCESS**, including protected execution/autonomy, full API regression, client state/export
- Vercel API Preview `dpl_E1emBBqmS4jz4VbMeZC6sAcHPiLp` — **READY**, exact integration SHA
- Vercel runtime error check — **no error clusters observed**

Current tree-identical release-refresh head `180943255e2a54f490c5f6375f559babd0e31454`, tested against current `main` at the time of refresh:

- Workstream Spec Validation `32648965379` — **SUCCESS**
- P2 CI `32648965370` — **SUCCESS**
- Bounded Autonomy `32648965387` — **SUCCESS**

Direct Preview health probing is intercepted by Vercel Authentication before application routing; this is access protection, not an application failure. Protected Vercel fetch/share tooling remains available for deployment verification.

P2-V0.15.11 authentic DSPy evidence: compiler run `32621606396` SUCCESS, artifact `9488544665`, digest `sha256:0013879518c00b28119ea951756f0b795badb5c0f86199191bdb548c315f85b9`.

P2-V0.15.12 authentic DSPy evidence: compiler run `32645066528` SUCCESS, artifact `9494664770`, digest `sha256:167d86a3e4ffba7907823a17f46b91658e4f93a8e554af503721743a30b538d9`.

## Vercel production prerequisite architecture

Wave 2 production requires:

- private Vercel Blob for immutable source contents;
- `BLOB_READ_WRITE_TOKEN` for the accepted Python `vercel>=0.9,<0.10` Blob adapter;
- transactional source-lineage metadata/current-head CAS in production Postgres;
- one repository-scoped GitHub Vercel Connect connector per registered repository target, attached to `parallax-api` for the intended environments;
- one dedicated project-scoped Vercel Preview access credential per registered Preview target, stored as a sensitive Vercel environment variable;
- `PARALLAX_VERCEL_PREVIEW_TARGETS_JSON` containing each exact repository/Vercel target plus its `github_connector` and bounded `vercel_token_env` reference.

`VERCEL_OIDC_TOKEN` is **not** a manual deployment secret. Vercel injects and refreshes it on deployments, and the Wave 2 GitHub Connect adapter consumes that platform-provided token.

The connected Vercel action surface can inspect projects/deployments/logs, access protected deployments, and initiate deployments, but it does not expose Blob creation, Connect attachment, Vercel token creation, environment-variable mutation, or Vercel Access Token creation. No alternate installed management plugin providing those writes was found. Vercel management API operations require a Vercel Access Token; GitHub Actions OIDC is not a replacement for that general management credential.

## Validated Vercel provisioning automation

Ops PR #91 merged to `main` as `f14a94dcf503e8ebd13e1f256f884bb86574300c`. It adds `scripts/provision_wave2_vercel.py` plus deterministic safety tests.

The helper is bounded to canonical `parallax-api` and the registered `parallax` Preview target. It can:

- create/reuse private Blob `parallax-source-lineage` and require `BLOB_READ_WRITE_TOKEN` in Preview + Production;
- create/reuse and attach `github/parallax-runtime` to `parallax-api` Preview + Production;
- create a Vercel access token scoped only to registered target project `prj_wLXC5JjjetJf0H97kncRlqczD3OC` and prove it cannot access `parallax-api`;
- retain the one-time target token only in process memory and pass it through stdin to sensitive `PARALLAX_VERCEL_TOKEN_PARALLAX`;
- install exact `PARALLAX_VERCEL_PREVIEW_TARGETS_JSON` in Preview + Production;
- verify required key names/connector presence;
- stop without applying migrations, merging PR #67, or deploying production.

Exact helper head `f37e5d4b586a8a990e654638e33336cdbaeeb580` passed P2 CI `32647389235` and Bounded Autonomy `32647389308`. Validation found and fixed command-argument secret redaction before merge.

Ops PR #92 merged the fail-closed self-reporting runner to `main` as `389546f963a71ecc912f755e879a2dcd2d4fd3a9`. `.github/workflows/wave2-vercel-provision-run.yml`:

- accepts only opaque repository Actions secret `VERCEL_TOKEN`;
- pins Vercel CLI `58.4.4`;
- runs the validated provisioning helper;
- reports only success/failure outcomes to Control Tower issue #31, never secret values;
- supports `workflow_dispatch` for a manual rerun after the secret is configured;
- contains no production migration, PR merge, or deployment command.

PR #92 exact head `035451aab69f64eea2d483c6aaa12d3f4f8c0e7e` passed P2 CI `32649543633` and Bounded Autonomy `32649543636`, including full API regression, browser/Skia acceptance, protected promotion evaluation and DSPy release compilation.

A deliberate runner execution at commit `c88a2d4216f81498f0ce385e5193388c311a0416`, Actions run `32649207367`, self-reported: credential availability **failure**, CLI install **skipped**, provisioning **skipped**. This is authoritative evidence that repository Actions secret `VERCEL_TOKEN` is currently absent. No Blob store, Connect connector, target token or target-registry environment mutation occurred.

### Sole external release blocker

The only currently identified external authorization boundary is a temporary Vercel management Access Token made available to the repository as Actions secret **`VERCEL_TOKEN`**. The token must have sufficient team/project authority for the helper to create/connect the private Blob store, create/attach the GitHub connector, create a project-scoped target token, and update the bounded Vercel environment variables.

The token value must not be pasted into chat or committed. Once the secret exists, the already-merged `Wave 2 Vercel Provision Run` workflow can be run manually; successful self-reported provisioning evidence unlocks the remaining already-authorized release sequence. The bootstrap management token should be revoked after successful provisioning/verification because the runtime uses narrower per-target credentials thereafter.

## Production Supabase preflight

Production Supabase project `Parallax 2.0` / `kjyenifnfjqnzfgshpwg` is `ACTIVE_HEALTHY`, region `us-east-2`, Postgres `17.6.1.155`.

Production migration history currently ends at the applied Project migration `20260822230525 projects`. Wave 2 migrations remain unapplied:

- `20260822_0007_project_runtime_binding.sql`
- `20260823_0008_durable_source_lineage.sql`

Direct preflight SQL verified there are no migration collisions:

- `conversations.project_id`: absent;
- `engineering_runs.project_id`: absent;
- `source_lineage_manifests`: absent;
- `source_lineage_heads`: absent;
- both proposed Project FK constraints: absent;
- `projects.id`, `conversations.id`, and `engineering_runs.id`: all `varchar(36)`, matching the migration contract.

Pre-migration security advisor output contains existing `RLS Enabled No Policy` INFO notices on intentionally server-owned fail-closed tables and an unrelated leaked-password-protection WARN. No permissive RLS policy was added and no unrelated Auth setting was changed.

The migrations remain deliberately unapplied until successful Vercel prerequisite evidence exists, preventing a half-upgraded production release.

## Remaining authorized release sequence

After successful Vercel provisioning evidence, Control Tower is authorized to proceed without another approval:

1. rerun/confirm provisioning verification;
2. apply migration 0007 and verify columns/FKs/indexes;
3. apply migration 0008 and verify lineage tables/checks/FK/RLS/revoked `anon`/`authenticated` privileges;
4. rerun Supabase security/performance advisors and confirm no release-introduced critical findings;
5. refresh PR #67 merge-ref validation again if `main` has moved materially;
6. merge PR #67 to `main` at the validated expected head;
7. verify the exact Vercel production deployment SHA rather than assuming Git integration success;
8. verify `/health`, `/ready`, authentication, database/runtime/provider composition, durable lineage behavior, least-privilege target isolation, logs/runtime errors, and rollback readiness;
9. update authoritative records to distinguish MERGED, DEPLOYED and DEPLOYMENT-VERIFIED states.

PR #67 must not be described as deployed merely because a Preview is green.

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
- production client baseline: **v0.13.9 / DEPLOYED / VERIFIED**
- Wave 2 P2-V0.15.1–P2-V0.15.12: **VALIDATED / INTEGRATION-COMPLETE / RELEASE AUTHORIZED / VERCEL MANAGEMENT CREDENTIAL PENDING / NOT MERGED / NOT DEPLOYED**
- Wave 2 Vercel provisioning helper: **VALIDATED / MERGED TO MAIN**
- Wave 2 Vercel provisioning runner: **VALIDATED / MERGED TO MAIN / LAST RUN BLOCKED BEFORE PROVISIONING BY ABSENT `VERCEL_TOKEN`**
- Wave 2 migrations/storage: **CODE + PREFLIGHT VALIDATED / PRODUCTION NOT APPLIED OR PROVISIONED**
- Wave 2 provider clients/composition: **CODE VALIDATED / LIVE PRODUCTION CREDENTIAL BINDING NOT PROVISIONED OR VERIFIED**
- Wave 2 protected end-to-end reference loop: **DEMONSTRATED AT REPOSITORY/INTEGRATION-TEST LEVEL**
- Wave 3 inherited autonomous/optimization/stall-recovery policy: **AUTHORITATIVE GOVERNANCE / RUNTIME NOT YET IMPLEMENTED**

## Authoritative-record status

- `CURRENT-STATE.md`: updated for standing release authorization, current tree-identical Wave 2 release-refresh validation, clean production migration preflight, merged provisioning helper/runner, and definitive evidence that the temporary Vercel management credential is the sole remaining external release blocker.
- `ARCHITECTURE.md`: remains v2.4 because the Wave 2 runtime/composition has not yet been merged/deployment-verified as production architecture.
- `PROJECT-CONSTITUTION.md`: remains v1.3; the operator authorized this release sequence but no durable governance authority boundary changed.
- `DESIGN-SYSTEM.md`: remains v2.1; no durable design-system rule changed.

Historical worker, integration, CI, provisioning-attempt, preview and production evidence remains preserved in GitHub Actions, issues/PRs, Supabase, and Vercel history.
