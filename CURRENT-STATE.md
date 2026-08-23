# Parallax 2.0 Current State

Release: App-builder Wave 2 production runtime; Wave 3 development integration in progress
Date: 2026-08-23
Status: **WAVE 2 = MERGED / PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED; WAVE 3 = DEVELOPMENT INTEGRATED THROUGH P2-V0.16.4 / CUMULATIVELY VALIDATED / NOT MERGED TO MAIN / NOT DEPLOYED**

## Production truth

Wave 2 is now the verified production app-builder runtime. The complete `P2-V0.15.1` through `P2-V0.15.12` tranche was provisioned, migrated, validated, merged and deployed through the guarded release sequence.

The production application merge is:

- PR `#67` — merged;
- merge commit `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- `main` was verified at that exact merge SHA immediately after promotion;
- later root documentation/authoritative-record commits do not redefine the deployed application release identity.

## Wave 3 development truth

Wave 3 development is active on the serialized integration branch `integration/wave3-autonomy`. This is validated development state only; it has **not** been merged to `main`, deployed to production, had Wave 3 migration `0009` applied to production, or been deployment-verified.

Validated integrated Wave 3 capabilities:

1. `P2-V0.16.1` / #95 — durable worker lifecycle, renewable leases, canonical checkpoints, stall classification, bounded recovery/reassignment and stale-worker fail-closed behavior;
2. `P2-V0.16.2` / #96 — protected deterministic browser/accessibility/network/layout validation, provenance-bound screenshot regression and secondary multimodal visual review;
3. `P2-V0.16.3` / #97 — bounded autonomous defect normalization, diagnose/correct/revalidate convergence, last-known-good preservation, finite resource/no-progress/oscillation bounds and data-only failure dispatch;
4. `P2-V0.16.4` / #98 — deterministic dependency/critical-path scheduling, integration backpressure, #95-bound work stealing, conservative change-impact validation, provenance-safe environment/pattern/repair reuse, bounded model routing, spec preflight, non-authoritative speculative integration, acceptance-preserving workstream sizing and privacy-safe development-performance telemetry.

Current serialized Wave 3 integration head after #98:

`04bc849faaf193a757d7da45823cf5ab700c1bde`

Cumulative exact-head evidence on that integration tree:

- Workstream Spec Validation `32673761335` — **SUCCESS**;
- Bounded Autonomy Pilot `32673761305` — **SUCCESS**;
- Parallax P2 CI `32673761323` — **SUCCESS**;
  - full API + contract regression — success;
  - client type/state/export + browser/Skia acceptance — success;
  - protected promotion evaluation — success;
  - DSPy release compilation — success.

The #98 validation cycle exposed and corrected a canonical graph node-order round-trip mismatch. Final reconciliation also bound work-steal proposals to dependency-ready work and the exact optimization-graph digest before the existing P2-V0.16.1 lease/generation/CAS reassignment authority can be invoked. No protected threshold, mutation, evaluator, worker identity, provider target or promotion boundary was weakened.

Next critical-path workstream is `P2-V0.16.5` / #99: serialize Wave 3 into the protected reference-app and autonomous recovery proof, including deliberate worker/process loss, functional/visual defects, stale-worker rejection, LKG/convergence cases, optimization non-authority and Project-isolation evidence. Passing that workstream stops at READY FOR PRODUCTION PROMOTION; it does not authorize production deployment.

## Authoritative governance

- `PROJECT-CONSTITUTION.md` v1.3 — unchanged;
- `ARCHITECTURE.md` v2.5 — unchanged by the Wave 3 development integration so far; the durable production architecture remains Wave 2 until promotion;
- `DESIGN-SYSTEM.md` v2.1 — unchanged;
- `CURRENT-STATE.md` — this production + validated-development snapshot;
- `PARALLEL-DEVELOPMENT.md` — concurrent-development protocol.

GitHub issues/PRs/workflows, Supabase migration/schema evidence and Vercel deployment/runtime evidence remain operational authority when chat recollection differs.

## Deployed Wave 2 capability

Production now composes:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> unchanged #46 protected evaluation -> operator REVIEW`

The deployed contracts include:

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
12. per-target provider credential isolation for multi-Project least privilege.

Process/request recreation, durable lineage reconstruction, duplicate IMPLEMENT prevention, duplicate provider-publication prevention and deliberate Project/spec/digest/lineage/stage/provider/Preview/evidence negative cases are protected. Vercel Preview remains the autonomous provider ceiling. Production merge/promotion remains an operator/release boundary.

## Final pre-merge validation

Final tree-identical Wave 2 release-refresh head:

`2cd5a29971912a896a379ff82725fbeb65e69d95`

Exact-head gates:

- Workstream Spec Validation `32662519994` — **SUCCESS**;
- Bounded Autonomy Pilot `32662519995` — **SUCCESS**;
- P2 CI `32662519996` — **SUCCESS**;
  - API + contract checks — success;
  - client type/state/export + browser/Skia acceptance — success;
  - protected promotion evaluation — success;
  - DSPy release compilation — success.

The merge used expected-head protection against `2cd5a299...`; GitHub returned merge commit `686d793...`.

## Vercel production prerequisites

Provisioning completed successfully before migrations/merge.

Successful protected provisioning evidence:

- runner commit `26672d5b7f45b27d64727f7f96ce3f60c5778027`;
- Actions run `32662010500`;
- credential availability — success;
- bootstrap access to both registered Vercel projects — success;
- canonical API project link — success;
- provision + verify — success;
- no secret values reported.

Provisioned production runtime dependencies:

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

The project-scoped Preview credential was verified to reach its registered `parallax` target and not `parallax-api`.

Live provisioning exposed and corrected several bootstrap assumptions before promotion: resumable Blob creation, canonical seeded project linking, team-wide connector discovery, current Vercel token JSON parsing and secret-safe environment upsert. The hardened provisioning implementation was promoted to `main` before the final Wave 2 merge.

## Production database

Production Supabase project `Parallax 2.0` / `kjyenifnfjqnzfgshpwg` is healthy.

Wave 2 migrations are applied and recorded:

- `20260823194237 project_runtime_binding`;
- `20260823194310 durable_source_lineage`.

Direct verification proved:

- `conversations.project_id` and `engineering_runs.project_id` exist with the expected type;
- both Project foreign-key constraints exist;
- `source_lineage_manifests` exists;
- `source_lineage_heads` exists;
- RLS is enabled on both lineage tables;
- `anon` and `authenticated` have no SELECT privilege on either lineage table.

Post-migration security/performance advisors introduced no release-blocking finding. RLS-with-no-policy notices on server-owned tables are intentional fail-closed INFO findings. The leaked-password-protection warning predates Wave 2 and was not changed as part of this release. New-index/foreign-key advisor entries are INFO only and are not evidence to remove fresh release indexes.

Wave 3 worker-recovery migration `20260823_0009_worker_recovery.sql` exists only in validated development state and remains unapplied to production.

## Production deployments

### API

`parallax-api` production deployment:

- deployment `dpl_h2JMsQJKSHUXazeCWGDSK9g1upKw`;
- exact GitHub SHA `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- commit verification — verified;
- target — production;
- state — **READY**;
- production alias `parallax-api-tan.vercel.app` points to the deployed release.

Live checks against the production alias:

- `GET /health` — **200**, service `parallax-api`, status `ok`;
- `GET /ready` — **200**, database `ok`, status `ready`;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- production runtime logs show the expected 200/200/401 requests on this exact deployment;
- runtime error clusters after deployment — **none observed**.

The exact immutable deployment hostname remains behind Vercel Deployment Protection and may return the Vercel SSO redirect before application routing; the production alias was used for application smoke checks.

### Client

`parallax` production deployment:

- deployment `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka`;
- exact GitHub SHA `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- commit verification — verified;
- target — production;
- state — **READY**;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app` and `parallax-git-main-lew7.vercel.app`;
- runtime error clusters after deployment — **none observed**.

Browser/Skia acceptance passed on the exact pre-merge application tree. Protected immutable deployment URLs may remain behind Vercel Deployment Protection.

## Provider/runtime verification boundary

Production prerequisite composition is real and verified: private Blob exists, durable lineage schema is active, `github/parallax-runtime` exists, the target-scoped Vercel credential/registry exist, both application deployments are on the exact merge SHA, readiness is healthy and protected auth fails closed.

A synthetic authenticated production GitHub/Preview mutation was **not** manufactured solely for post-deploy verification. Doing so would require consuming the production break-glass/session boundary and deliberately creating external repository/Preview state after the same provider/replay path had already passed the protected reference-app loop and negative cases at the exact release tree. The release therefore treats the protected reference loop + real production dependency composition + exact deployment/smoke/log evidence as the bounded verification proof, rather than widening production side effects for a redundant test.

## Rollback readiness

Rollback source remains available:

- previous API production deployment `dpl_8KLzBTY1zhvHkVqyH2MtKKBovz2K` is **READY** at pre-Wave-2 application main `9482cdf1068261f720389410dd0cb754e68e8c17`;
- prior client v0.13.9 deployment `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` is **READY** at `0938296be2c8b488340717fd5f6dbffad65d3856`.

Database rollback must respect the now-applied forward-compatible Project/lineage schema rather than destructively removing production migration history during an application rollback.

## Bootstrap credential cleanup

The temporary team-wide Vercel management Access Token used only for prerequisite provisioning was revoked after successful deployment verification.

Cleanup evidence:

- cleanup commit `0b6505b60cd4989467981ea345050f4d2bfd8e81` on the ops runner branch;
- Actions run `32663022035`;
- Vercel self-revoke — **SUCCESS**;
- post-revoke project-access proof — **SUCCESS**, Vercel rejected the same credential with HTTP 403;
- no token value was read or reported.

If GitHub still displays repository Actions secret `VERCEL_TOKEN`, its stored value is now revoked/inert. The connected GitHub tool surface does not expose repository-secret deletion, so deleting that inert secret entry is optional operator housekeeping rather than a live-authority blocker.

## Wave 2 completion decision

Wave 2 is **DEPLOYMENT-VERIFIED**.

Evidence satisfies the release objective without claiming unsupported facts:

- final cumulative candidate validated;
- production prerequisites provisioned and verified;
- production migrations applied and security posture verified;
- exact-head PR merged with head protection;
- exact merge SHA deployed to API and client;
- both deployments READY;
- health/readiness/auth boundary verified;
- production logs and runtime errors inspected;
- rollback targets verified;
- temporary broad bootstrap credential revoked.

## Wave 3 current decision

Wave 3 is **IN DEVELOPMENT** and cumulatively validated through `P2-V0.16.4` on the integration branch. This does not alter Wave 2 production truth.

The accepted Wave 3 development baseline now contains:

- durable worker lease/checkpoint/recovery semantics;
- deterministic browser/accessibility/network/layout validation before visual judgment;
- provenance-bound screenshot regression and bounded secondary multimodal review;
- autonomous diagnose/correct/retest with immutable lineage, strict LKG preservation, convergence/resource bounds and explicit human/resource stop conditions;
- deterministic dependency/critical-path scheduling, integration backpressure and safe-boundary cancellation;
- graph/lease/path-bound work stealing through the existing worker recovery authority;
- conservative impact-aware validation with full promotion gates preserved;
- immutable secret-free environment/cache identity, validated reusable patterns and Project-isolated repair memory;
- adaptive model routing inside approved capability classes;
- spec preflight, non-authoritative speculative integration and acceptance-preserving workstream sizing;
- bounded privacy-safe development-performance telemetry.

The remaining Wave 3 objective is the `P2-V0.16.5` final integration/reference-app/recovery proof. Production merge/promotion remains outside the ordinary autonomous Wave 3 ceiling unless durable governance is explicitly changed later.
