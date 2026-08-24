# Parallax 2.0 Current State

Release: App-builder Wave 3 production runtime
Date: 2026-08-23
Status: **WAVE 2 = HISTORICAL DEPLOYMENT-VERIFIED FOUNDATION; WAVE 3 = MERGED / PRODUCTION MIGRATED / PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5**

## Production truth

Wave 3 is now the verified production app-builder runtime. The accepted `P2-V0.16.1` through `P2-V0.16.5` tranche was integrated, exact-head validated, operator-authorized, merged through the guarded release path, migrated and deployment-verified without broadening the protected authority model.

The production application merge is:

- release issue `#121` — operator-authorized production promotion;
- release PR `#122` — merged to `main` with expected-head protection;
- exact validated candidate `c8c8def97e9a56cfd964fb589d5c718c253e8050`;
- production merge commit `cbe7a967e37b90e4254fe838aff831eafe33536b`;
- `main` had no drift against the candidate before promotion (`49` commits ahead / `0` behind);
- later documentation-only commits do not redefine the deployed application release identity.

Wave 2 remains the historical production-verified foundation beneath this release. Its application merge was `686d7934044e5018dc3cd324f0b61ee2b548c756`.

## Wave 3 production capability

Production now includes:

1. `P2-V0.16.1` / #95 — durable worker lifecycle, renewable leases, canonical checkpoints, stall classification, bounded recovery/reassignment and stale-worker fail-closed behavior;
2. `P2-V0.16.2` / #96 — protected deterministic browser/accessibility/network/layout validation, provenance-bound screenshot regression and secondary multimodal visual review;
3. `P2-V0.16.3` / #97 — bounded autonomous defect normalization, diagnose/correct/revalidate convergence, last-known-good preservation, finite resource/no-progress/oscillation bounds and data-only failure dispatch;
4. `P2-V0.16.4` / #98 — deterministic dependency/critical-path scheduling, integration backpressure, #95-bound work stealing, conservative change-impact validation, provenance-safe environment/pattern/repair reuse, bounded model routing, spec preflight, non-authoritative speculative integration, acceptance-preserving workstream sizing and privacy-safe development-performance telemetry;
5. `P2-V0.16.5` / #99 — permanent integrated reference-app/recovery proof composing the accepted Wave 2 route with Wave 3 worker recovery, browser/visual precedence, autonomous correction, optimization non-authority, replay-safe Preview delivery, protected evaluation and explicit operator REVIEW.

The protected runtime path is therefore:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> deterministic browser/accessibility/console/network/layout validation -> screenshot regression -> bounded multimodal review -> bounded correction/retry with LKG + convergence limits -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> unchanged protected AppBuilder evaluation -> explicit operator REVIEW`

The worker recovery path is server-owned and durable. Process loss can move `CHECKPOINTED -> STALLED -> RECOVERING -> REASSIGNED` on the same worker execution identity with a lease-generation increment. Stale pre-loss workers fail closed. A recovered execution resumes from canonical Project/run/spec/source-lineage/LKG checkpoint state rather than requiring manual Engineering Run `resume`.

The permanent reference proof also verifies exact IMPLEMENT replay, replay-safe Git/Preview identities, deterministic evidence precedence over visual judgment, fresh-lineage correction, regression/LKG protection, repeated-defect/no-progress/oscillation limits, provider-vs-human recovery classification, optimization non-authority, Project-private evidence isolation and unchanged protected scoring.

Vercel Preview remains the autonomous provider ceiling. Production promotion remains an explicit operator/release authority.

## Release validation

The exact production candidate `c8c8def97e9a56cfd964fb589d5c718c253e8050` was validated again on release PR #122 immediately before merge:

- Workstream Spec Validation `32676226909` — **SUCCESS**;
- Bounded Autonomy Pilot `32676226899` — **SUCCESS**;
- Parallax P2 CI `32676226915` — **SUCCESS**;
  - full API + contract regression — success;
  - permanent Wave 3 reference/recovery tests — success;
  - client type/state/export + browser/Skia acceptance — success;
  - protected promotion evaluation — success;
  - DSPy release compilation — success.

P2-V0.16.5 also retains authentic spec-first DSPy evidence: SpecCritic/SpecCompiler run `32674257003` succeeded and its protected compiled plan was committed before implementation.

## Authoritative governance

- `PROJECT-CONSTITUTION.md` v1.3 — unchanged;
- `ARCHITECTURE.md` v2.6 — updated for the deployed Wave 3 runtime;
- `DESIGN-SYSTEM.md` v2.1 — unchanged;
- `CURRENT-STATE.md` — this deployment-verified Wave 3 production snapshot;
- `PARALLEL-DEVELOPMENT.md` — concurrent-development protocol.

GitHub issues/PRs/workflows, Supabase migration/schema evidence and Vercel deployment/runtime evidence remain operational authority when chat recollection differs.

## Durable production foundations

The deployed contracts continue to include:

1. canonical Project/runtime identity and owner-scoped binding;
2. protected Project/run workspace identity and immutable source lineage;
3. typed protected IMPLEMENT generation/mutation;
4. project-scoped tool authority;
5. private immutable source objects plus transactional lineage/head metadata;
6. exact-lineage Vercel Sandbox BUILD/TEST/VERIFY;
7. concrete bounded GitHub and Vercel Preview clients;
8. client Project select/create and canonical `project_id` Code compatibility;
9. first-run repository bootstrap and replay-safe GitHub/Preview publication;
10. protected #46 evaluation derived from persisted runtime/provider facts;
11. live production dependency/credential composition and lineage-table security hardening;
12. per-target provider credential isolation for multi-Project least privilege;
13. durable worker execution/lease/checkpoint/recovery state;
14. deterministic browser/accessibility/network/layout evidence before visual judgment;
15. autonomous correction with strict LKG/convergence/resource controls;
16. conservative optimization controls that cannot weaken promotion requirements.

Process/request recreation, durable lineage reconstruction, duplicate IMPLEMENT prevention, duplicate provider-publication prevention and deliberate Project/spec/digest/lineage/stage/provider/Preview/evidence negative cases remain protected.

## Production prerequisites

The Wave 2 production prerequisite composition remains active and was not broadened for Wave 3:

- private Blob store `parallax-source-lineage`;
- `BLOB_READ_WRITE_TOKEN` available to Preview + Production for the accepted Python Blob adapter;
- GitHub Vercel Connect connector `github/parallax-runtime`;
- connector attached to `parallax-api` for Preview + Production;
- dedicated Vercel credential scoped only to target project `parallax`;
- sensitive `PARALLAX_VERCEL_TOKEN_PARALLAX` for Preview + Production;
- exact `PARALLAX_VERCEL_PREVIEW_TARGETS_JSON` target registration.

Canonical target remains:

- repository: `github:Ryan9876/parallax` / GitHub repo ID `1340272514`;
- production branch: `main`;
- GitHub connector: `github/parallax-runtime`;
- Vercel Preview ref: `vercel:preview:parallax`;
- Vercel project ID: `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- team ID: `team_JgE8AWWz36uzRbeR6V6EWg9k`;
- Vercel token env reference: `PARALLAX_VERCEL_TOKEN_PARALLAX`.

The project-scoped Preview credential remains isolated from the API project.

## Production database

Production Supabase project `Parallax 2.0` / `kjyenifnfjqnzfgshpwg` is healthy.

Relevant production migrations now include:

- `20260823194237 project_runtime_binding`;
- `20260823194310 durable_source_lineage`;
- `20260824002126 worker_recovery` — production application of repository migration `20260823_0009_worker_recovery.sql`.

Wave 3 migration verification proved:

- `engineering_worker_executions` exists in `public`;
- one execution per Engineering Run is enforced by the unique `run_id` boundary;
- the Engineering Run foreign key exists with cascade cleanup;
- worker state, nonnegative counters/revisions, lease pairing, bounded checkpoint size, lineage/fingerprint formats and lease-owner format are protected by database constraints;
- worker state and lease-expiry indexes exist;
- RLS is enabled;
- `anon` and `authenticated` have no SELECT privilege;
- security advisors report only the expected INFO `RLS enabled / no policy` notice for server-owned fail-closed tables plus the pre-existing leaked-password-protection warning;
- performance advisors add only fresh/unused-index INFO notices and pre-existing informational findings; no Wave 3 release blocker was introduced.

The server-owned worker table intentionally has no direct client RLS policy because direct `anon`/`authenticated` privileges are revoked and FastAPI remains the application authorization boundary.

## Production deployments

### API — Wave 3

`parallax-api` production deployment:

- deployment `dpl_q56DQQZgB6CBoSp8Bh9R5hCPrphr`;
- exact GitHub SHA `cbe7a967e37b90e4254fe838aff831eafe33536b`;
- GitHub commit verification — verified;
- target — production;
- state — **READY**;
- production aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app` and `parallax-api-git-main-lew7.vercel.app`.

Live checks against the production alias:

- `GET /health` — **200**, service `parallax-api`, status `ok`;
- `GET /ready` — **200**, database `ok`, status `ready`;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- exact-deployment runtime logs show the expected 200/200/401 requests;
- runtime error clusters after deployment — **none observed**.

### Client

Wave 3 changed no client-source path. Vercel correctly canceled the attempted main-branch client deployment `dpl_9JEQDaNBajvCiKku4qHmnrPt2aDX` because the configured Ignored Build Step found no change under the client project root.

The active production client therefore remains the already deployment-verified artifact:

- deployment `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka`;
- source SHA `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- target — production;
- state — **READY**;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app` and `parallax-git-main-lew7.vercel.app`.

This is expected release behavior, not a partial deployment: the Wave 3 tranche modified the API/runtime, validation, recovery and database paths but did not modify `apps/client`.

## Provider/runtime verification boundary

Production prerequisite composition remains real and verified: private Blob exists, source-lineage and worker-recovery schema are active, `github/parallax-runtime` exists, the target-scoped Vercel credential/registry exists, the API deployment is on the exact Wave 3 merge SHA, readiness is healthy and protected auth fails closed.

A synthetic authenticated production GitHub/Preview mutation was not manufactured solely for post-deploy verification. The permanent protected reference loop already proves the same provider/replay path with deliberate negative cases at the exact release tree; production verification therefore uses real dependency composition, exact deployment identity, database schema evidence, public readiness/auth probes and runtime-error inspection without widening production side effects.

## Rollback readiness

Immediate application rollback targets remain available:

- previous API Wave 2 production deployment `dpl_h2JMsQJKSHUXazeCWGDSK9g1upKw` is **READY** at `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- current client production deployment `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka` remains **READY** at the same Wave 2 source SHA because no Wave 3 client code changed.

Earlier rollback sources also remain available, including API `dpl_8KLzBTY1zhvHkVqyH2MtKKBovz2K` at `9482cdf1068261f720389410dd0cb754e68e8c17` and client `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` at `0938296be2c8b488340717fd5f6dbffad65d3856`.

Database rollback must respect the now-applied forward-compatible Project/lineage/worker-recovery schema rather than destructively removing migration history during an application rollback.

## Bootstrap credential cleanup

The temporary team-wide Vercel management Access Token used only for Wave 2 prerequisite provisioning remains revoked/inert. Wave 3 promotion required no new broad provisioning credential.

## Wave 3 completion decision

Wave 3 is **PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED**.

Evidence satisfies the release objective without claiming unsupported facts:

- complete Wave 3 candidate integrated and cumulatively validated;
- operator authorization recorded in #121;
- candidate confirmed ahead-only from current `main` before release;
- exact-head release gates passed on PR #122;
- PR #122 merged with expected-head protection;
- worker-recovery migration applied and security/schema boundaries verified;
- exact Wave 3 merge SHA deployed to `parallax-api`;
- API deployment READY;
- client path correctly skipped because no client code changed, preserving the existing READY production artifact;
- health/readiness/auth boundary verified;
- production logs and runtime errors inspected;
- rollback targets verified;
- no protected threshold, canonical identity, accepted lineage, single-writer worker authority, deterministic validation precedence, correction bound, provider target or production-control boundary was weakened.

The next product phase is Wave 4 UX and operating efficiency on top of this verified runtime.