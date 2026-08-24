# Parallax 2.0 Current State

Release: App-builder Wave 3 production runtime + production hotfixes
Date: 2026-08-23
Status: **WAVE 3 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; PROJECT-CREATE AND AUTONOMOUS-RUN PRODUCTION REGRESSIONS CORRECTED THROUGH HOTFIX #134**

## Production truth

Wave 3 remains the deployed app-builder runtime through `P2-V0.16.5`. Its guarded production release was completed under #121/#122 with application merge `cbe7a967e37b90e4254fe838aff831eafe33536b`, worker-recovery migration `20260824002126 worker_recovery`, and deployment verification.

Three operator-discovered production regressions were subsequently corrected without weakening canonical Project identity, source lineage, provider credential scope, protected evaluation, deterministic validation precedence, worker authority, publication safety, or explicit production-promotion authority.

The current repository `main` application head after the third hotfix is:

- `389ef2ab17999db23abd7f4a77ea616b7ba5252b` — production hotfix #134 merge.

Because the hotfixes affect different deployable roots, current production artifacts intentionally have different exact source SHAs:

- client: hotfix #125 source `c088c363f75e7b825fc417441649f9e5069606ff`;
- API: hotfix #134 source `389ef2ab17999db23abd7f4a77ea616b7ba5252b`.

## Wave 3 production capability

Production retains the complete protected Wave 3 route:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> deterministic browser/accessibility/console/network/layout validation -> screenshot regression -> bounded multimodal review -> bounded correction/retry with LKG + convergence limits -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> protected AppBuilder evaluation -> explicit operator REVIEW`

Durable worker recovery, stale-worker rejection, replay-safe mutation/publication, last-known-good preservation, bounded correction, protected deterministic-browser precedence, privacy-safe reuse/telemetry, and explicit production authority remain unchanged.

## Production hotfix #125 — Project repository shorthand

Operator production testing found that the Project-create form accepted natural GitHub shorthand such as `ryan9876/parallax` but forwarded it unchanged, while the backend correctly requires canonical provider-qualified repository identity.

Correction:

- PR #125 validated and operator-authorized;
- client normalizes only valid two-segment GitHub shorthand `owner/repository` to `github:owner/repository` before Project creation;
- backend Project validation remains unchanged;
- canonical server-returned `Project.id` remains the only Code execution binding authority;
- mobile Project-create browser coverage proves the normalization path.

Production evidence:

- production merge `c088c363f75e7b825fc417441649f9e5069606ff`;
- production client deployment `dpl_CKmaLXMvrcjBgxo2zum6mQthtDnj` — **READY** on the exact merge SHA;
- production alias `parallax-ashy-one-20.vercel.app` points to that client release;
- operator retest confirmed Project `Parallax logo` was successfully created and selected, resolving the original 422 regression;
- issue #124 is closed completed.

## Production hotfix #131 — GitHub repository casing

During the next operator test, `Run autonomously` reached production twice but both calls returned 503 while the Engineering Run remained safely in `PLAN`.

Persisted evidence identified the exact mismatch:

- Project repository ref: `github:ryan9876/parallax`;
- registered production target: `github:Ryan9876/parallax`;
- run: `a62f8dbd-4ba5-4fb2-a7a5-3c162b61ea8d`, state `PLAN`, revision `1` before correction.

GitHub repository owner/name identity is case-insensitive, but the production target resolver and GitHub installation-scope verifier were comparing those strings case-sensitively.

Correction in PR #131:

- case-fold only the GitHub `owner/repository` identity used for target lookup and installation-scope comparison;
- preserve the persisted Project repository ref rather than mutating production data to mask the defect;
- reject duplicate registered GitHub targets that differ only by casing;
- leave Vercel refs, GitHub repo IDs, connector references, credential resources, Project IDs, durable lineage, tool authority and production authority unchanged.

Exact-head validation on `cfb6bff885f22dbfc712e4df9c6208a2d31e6b3d`:

- Parallax P2 CI `32679644684` — **SUCCESS**;
  - API + contract regression — success;
  - client + browser/Skia acceptance — success;
  - protected promotion evaluation — success;
  - DSPy release compilation — success;
- Bounded Autonomy Pilot `32679644621` — **SUCCESS**;
- Vercel Preview checks for both client and API — success.

Operator authorization was received before production mutation.

Production evidence:

- PR #131 merged with expected-head protection;
- production merge `23678383a0a97dfc3df4feadecba507eb290f6ae`;
- production API deployment `dpl_7Pk1j3oBe3YvgcbRunP9JF8yBzVZ` — **READY** on that exact SHA;
- production aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`;
- `GET /health` — **200**, service `parallax-api`, status `ok`;
- `GET /ready` — **200**, database `ok`, status `ready`;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- runtime error clusters in the immediate post-deploy window — **none observed**.

The authenticated autonomous-run functional confirmation remained an operator retry against the preserved existing run; no synthetic authenticated production mutation was manufactured solely for deployment verification.

## Production hotfix #134 — repository bootstrap source projection

The operator retry after #131 still returned 503 twice while the preserved Engineering Run remained safely in `PLAN`. No worker execution row, IMPLEMENT attempt, source mutation, branch, commit, PR, or Preview publication was created by the failed retries.

The failure was narrowed to repository-backed durable source bootstrap before worker execution. Two contract mismatches were identified:

1. tracked `.env.example` files were admitted by the GitHub source-read path contract even though durable lineage correctly rejects every `.env*` filename;
2. the canonical repository read model reused a publication-oriented secret-literal heuristic, causing legitimate auth/security source files containing code or test fixtures with words such as `token`, `secret`, `password`, or `authorization` to be rejected before lineage initialization.

Correction in PR #134:

- add a deterministic lineage-safe repository projection for missing root lineage bootstrap;
- exclude `.env*`, `.git`, `.ssh`, known credential/secret filenames, and private-key/certificate suffixes before any provider file-content read;
- excluded content never enters the source package, durable lineage, model/source context, sandbox transfer, mutation, or publication;
- allow bounded UTF-8 source from the already-authorized canonical repository to contain credential-related implementation syntax and test fixtures;
- keep strict secret-literal rejection unchanged on `GitHubCommitFile`, so suspicious credential-bearing output still cannot be published;
- preserve exact canonical Project/run identity, repository revision, provider authorization/audit, GitHub installation scope, Vercel target scope, content addressing, accepted-lineage semantics, replay behavior, and production authority;
- record root-lineage source provenance with projection identity `lineage-safe-v2`;
- add a permanent self-hosting regression gate that evaluates the current checked-out Parallax repository against the production bootstrap source contract.

Exact-head validation on `a00b278f1a6174e877169c972fc5e0dcc725b2a1`:

- Parallax P2 CI `32681790575` — **SUCCESS**;
  - API + contract regression — success;
  - client + browser/Skia acceptance — success;
  - protected promotion evaluation — success;
  - DSPy release compilation — success;
- Bounded Autonomy Pilot `32681790561` — **SUCCESS**;
- Vercel Preview checks for `parallax` and `parallax-api` — success.

Operator authorization was received before production mutation.

Production evidence:

- PR #134 merged with expected-head protection;
- production merge `389ef2ab17999db23abd7f4a77ea616b7ba5252b`;
- production API deployment `dpl_2bE5DEjCQtE2xDBgSnojAsuZKEdo` — **READY** on that exact merge SHA;
- production aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`;
- `GET /health` — **200**, service `parallax-api`, status `ok`;
- `GET /ready` — **200**, database `ok`, status `ready`;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- production runtime error clusters in the immediate post-deploy window — **none observed**;
- the client production build for the API-only merge was path-filtered/canceled, intentionally preserving verified client deployment `dpl_CKmaLXMvrcjBgxo2zum6mQthtDnj` at `c088c363f75e7b825fc417441649f9e5069606ff`.

The original authenticated `Parallax logo` run remains preserved for operator functional confirmation. Deployment verification deliberately did not manufacture a synthetic authenticated production mutation.

## Production database

Production Supabase project `Parallax 2.0` / `kjyenifnfjqnzfgshpwg` remains healthy. Relevant migrations remain:

- `20260823194237 project_runtime_binding`;
- `20260823194310 durable_source_lineage`;
- `20260824002126 worker_recovery`.

None of production hotfixes #125, #131, or #134 required a database migration or schema mutation.

## Production provider prerequisites

The existing least-privilege production composition remains active and unchanged:

- private Blob store `parallax-source-lineage`;
- `BLOB_READ_WRITE_TOKEN` for the accepted server-owned lineage adapter;
- GitHub Vercel Connect connector `github/parallax-runtime`;
- target-scoped Vercel credential `PARALLAX_VERCEL_TOKEN_PARALLAX`;
- server-owned `PARALLAX_VERCEL_PREVIEW_TARGETS_JSON` registry;
- registered repository target `github:Ryan9876/parallax`, GitHub repo ID `1340272514`;
- Vercel Preview project `prj_wLXC5JjjetJf0H97kncRlqczD3OC`, team `team_JgE8AWWz36uzRbeR6V6EWg9k`.

Provider-native GitHub owner/repository casing equivalence is recognized at the matching boundary. Repository bootstrap now applies the durable lineage secret-path boundary before provider file reads, while publication retains its stricter output secret-literal guard. No broader provider identity or credential scope was introduced.

## Rollback readiness

Immediate rollback artifacts remain available:

- previous API hotfix #131 deployment `dpl_7Pk1j3oBe3YvgcbRunP9JF8yBzVZ` — **READY** at `23678383a0a97dfc3df4feadecba507eb290f6ae`;
- earlier API Wave 3 deployment `dpl_q56DQQZgB6CBoSp8Bh9R5hCPrphr` — **READY** at `cbe7a967e37b90e4254fe838aff831eafe33536b`;
- pre-hotfix client deployment `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka` remains available at `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- current client deployment `dpl_CKmaLXMvrcjBgxo2zum6mQthtDnj` and current API deployment `dpl_2bE5DEjCQtE2xDBgSnojAsuZKEdo` are both verified production artifacts.

Database rollback continues to preserve the forward-compatible Project/lineage/worker-recovery schema rather than destructively removing migration history.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.3 — unchanged; governance/authority did not change;
- `ARCHITECTURE.md` v2.6 — unchanged; hotfix #134 corrects implementation behavior inside the existing bounded repository/bootstrap and publication trust boundaries rather than changing the durable architecture;
- `DESIGN-SYSTEM.md` v2.1 — unchanged;
- `CURRENT-STATE.md` — updated for the deployment-verified #134 production state.

## Current decision

Wave 3 plus production hotfixes #125, #131, and #134 are **PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED** at the infrastructure, persistence, provider, and security boundaries.

The next operator action is to retry **Run autonomously** on the preserved `Parallax logo` Project/run `a62f8dbd-4ba5-4fb2-a7a5-3c162b61ea8d`. Success should now pass repository bootstrap and advance into the protected worker/IMPLEMENT path. If a different failure occurs, treat it as new production evidence rather than weakening the accepted runtime contracts.

Wave 4 product UX and operating efficiency remains the next planned product phase after this functional production retest.