# Parallax 2.0 Current State

Release: App-builder Wave 3 production runtime + production hotfixes
Date: 2026-08-23
Status: **WAVE 3 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; PRODUCTION HOTFIXES #125, #131, #134, AND #137 DEPLOYED / DEPLOYMENT-VERIFIED; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Production truth

Wave 3 remains the deployed app-builder runtime through `P2-V0.16.5`. Its guarded production release was completed under #121/#122 with application merge `cbe7a967e37b90e4254fe838aff831eafe33536b`, worker-recovery migration `20260824002126 worker_recovery`, and deployment verification.

Four operator-discovered production regressions have now been corrected without weakening canonical Project identity, source lineage, provider credential scope, protected evaluation, deterministic validation precedence, worker authority, publication safety, rollback, or production-control boundaries.

The current repository `main` application head after production hotfix #137 is:

- `9ea97b3184d155ed954cdf9d5f95e2a289e95a8e` — production hotfix #137 merge.

Because the hotfixes affect different deployable roots, current production artifacts intentionally have different exact source SHAs:

- client: hotfix #125 source `c088c363f75e7b825fc417441649f9e5069606ff`, deployment `dpl_CKmaLXMvrcjBgxo2zum6mQthtDnj`;
- API: hotfix #137 source `9ea97b3184d155ed954cdf9d5f95e2a289e95a8e`, deployment `dpl_GcmK9zYkGoy86mxwyq1X2NSC54ux`.

Production regression #136 is resolved. The Vercel Connect connector wire contract now encodes `github/parallax-runtime` as one path parameter, and the exact production deployment passed a real read-only Vercel OIDC -> Vercel Connect -> exact GitHub installation/repository/production-branch preflight before cutover.

## Standing single-user production promotion authority

On 2026-08-23 the project owner granted standing authorization for Parallax's own validated releases and hotfixes to be promoted to production without a separate per-release approval while Parallax remains effectively single-user.

This standing authorization applies only to promotion of a release candidate that has already passed the applicable exact-head release gates and has an acceptable rollback/forward-recovery path. It does not waive required CI, protected evaluation, source/provider/security boundaries, deployment evidence, or rollback requirements, and it does not pre-authorize unrelated destructive database changes, data loss, materially broader credential/provider authority, or other materially different high-risk mutations.

The standing authorization expires automatically when additional real users begin relying on Parallax production, or earlier if the owner revokes it. When that condition is reached, explicit per-release production authority must be re-established.

Hotfix #137 was the first release promoted under this standing authority. No additional per-release approval was requested after its final exact head passed the required gates.

## Wave 3 production capability

Production retains the complete protected Wave 3 route:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> deterministic browser/accessibility/console/network/layout validation -> screenshot regression -> bounded multimodal review -> bounded correction/retry with LKG + convergence limits -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> protected AppBuilder evaluation -> explicit operator REVIEW`

Durable worker recovery, stale-worker rejection, replay-safe mutation/publication, last-known-good preservation, bounded correction, protected deterministic-browser precedence, privacy-safe reuse/telemetry, and explicit production authority remain unchanged. The standing authorization changes Parallax self-development release procedure only; it does not silently grant Parallax-developed Projects or their runtime agents unrestricted production deployment authority.

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
- Bounded Autonomy Pilot `32679644621` — **SUCCESS**;
- Vercel Preview checks for both client and API — success.

Production evidence:

- PR #131 merged with expected-head protection;
- production merge `23678383a0a97dfc3df4feadecba507eb290f6ae`;
- production API deployment `dpl_7Pk1j3oBe3YvgcbRunP9JF8yBzVZ` — **READY** on that exact SHA;
- `GET /health` — **200**;
- `GET /ready` — **200**;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- runtime error clusters in the immediate post-deploy window — none observed.

## Production hotfix #134 — repository bootstrap source projection

The operator retry after #131 still returned 503 while the preserved Engineering Run remained safely in `PLAN`. No worker execution row, IMPLEMENT attempt, source mutation, branch, commit, PR, or Preview publication was created by the failed retries.

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
- Bounded Autonomy Pilot `32681790561` — **SUCCESS**;
- Vercel Preview checks for `parallax` and `parallax-api` — success.

Production evidence:

- PR #134 merged with expected-head protection;
- production merge `389ef2ab17999db23abd7f4a77ea616b7ba5252b`;
- production API deployment `dpl_2bE5DEjCQtE2xDBgSnojAsuZKEdo` — **READY**;
- `GET /health` — **200**;
- `GET /ready` — **200**;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- production runtime error clusters in the immediate post-deploy window — none observed.

## Production hotfix #137 — Vercel Connect connector wire path and production provider preflight

Production evidence after #134 showed the preserved autonomous run still returning HTTP 503 before any root source-lineage manifest/head or worker execution row was created.

Diagnosis:

- `VercelConnectGitHubCredentialProvider` used `quote(connector, safe='/')` for connector `github/parallax-runtime`;
- Vercel Connect defines the connector as one path parameter and requires slash-bearing identifiers to be percent-encoded, e.g. `github%2Fparallax-runtime`;
- the existing test asserted decoded `request.url.path`, which could not distinguish the incorrect raw URL from the required wire representation and therefore allowed CI to pass incorrectly.

Correction in PR #137:

- encode the complete connector path parameter with `quote(..., safe='')`;
- add a raw-wire-path regression requiring `/v1/connect/token/github%2Fparallax-runtime`;
- keep the GitHub Connect connector production-only after direct Preview evidence returned `403 Connector is not enabled for this environment`;
- add a production-only, read-only Vercel build preflight that uses the deployment OIDC identity and the server-owned target registry to verify the encoded Connect exchange, exactly one GitHub installation repository, matching repository numeric ID, registered production branch resolution, and presence of the target-scoped Vercel Preview credential before production cutover;
- Preview skips the Connect preflight but still builds the actual Python API function bundle;
- preserve Project/repository identity, source-lineage safety, provider scope, protected evaluation, and rollback boundaries.

Temporary diagnostic endpoints and canary workflows used during diagnosis were removed before the final candidate.

Final exact-head validation on `8b3849cfc24beef75e9ecd0282b4b04b6ec9d32e`:

- reconciled to current `main`: ahead 19 / behind 0;
- Parallax P2 CI `32684841737` — **SUCCESS**;
  - Fast API + contract checks — success;
  - Fast client/browser/Skia acceptance — success;
  - Protected promotion evaluation — success;
  - DSPy release compilation — success;
- Bounded Autonomy Pilot `32684841734` — **SUCCESS**;
- Vercel `parallax` status — success;
- Vercel `parallax-api` status — success;
- API-bearing Preview `dpl_2ZM6Z4KyzyfVRu1bJgZyDZFVzcZy` — **READY**, with logs proving the production provider preflight correctly skipped in Preview while the Python API bundle still built successfully.

Production promotion used the standing single-user authority recorded in `PROJECT-CONSTITUTION.md` v1.4.

Production evidence:

- PR #137 merged with exact-head protection;
- production merge `9ea97b3184d155ed954cdf9d5f95e2a289e95a8e` — GitHub verified;
- production API deployment `dpl_GcmK9zYkGoy86mxwyq1X2NSC54ux` — **READY** on that exact SHA;
- immutable URL `parallax-f02jmcd6n-lew7.vercel.app`;
- aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`;
- production build log — **`Production provider preflight: PASS (1 registered target(s))`** before Python bundle build/deployment;
- `GET /health` — **200**, service `parallax-api`, status `ok`;
- `GET /ready` — **200**, database `ok`, status `ready`;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge;
- production runtime error clusters in the immediate post-deploy window — **none observed**;
- deployment-scoped runtime logs contain only expected smoke/auth-boundary traffic for the verification window.

The exact provider failure that caused #136 is therefore deployment-verified as corrected at its real production boundary. The preserved authenticated `Parallax logo` Engineering Run was not synthetically replayed without a user session solely to manufacture end-to-end evidence; lack of that replay does not weaken the direct production provider-chain proof above.

## Production database

Production Supabase project `Parallax 2.0` / `kjyenifnfjqnzfgshpwg` remains healthy. Relevant migrations remain:

- `20260823194237 project_runtime_binding`;
- `20260823194310 durable_source_lineage`;
- `20260824002126 worker_recovery`.

None of production hotfixes #125, #131, #134, or #137 required a database migration or schema mutation.

## Production provider prerequisites

The existing least-privilege production composition remains active:

- private Blob store `parallax-source-lineage`;
- `BLOB_READ_WRITE_TOKEN` for the accepted server-owned lineage adapter;
- production-only GitHub Vercel Connect connector `github/parallax-runtime`;
- target-scoped Vercel credential `PARALLAX_VERCEL_TOKEN_PARALLAX`;
- server-owned `PARALLAX_VERCEL_PREVIEW_TARGETS_JSON` registry;
- registered repository target `github:Ryan9876/parallax`, GitHub repo ID `1340272514`;
- Vercel Preview project `prj_wLXC5JjjetJf0H97kncRlqczD3OC`, team `team_JgE8AWWz36uzRbeR6V6EWg9k`.

Provider-native GitHub owner/repository casing equivalence is recognized at the matching boundary. Repository bootstrap applies the durable lineage secret-path boundary before provider file reads, publication retains its stricter output secret-literal guard, and the Connect connector remains production-scoped. The production preflight verifies this existing authority rather than broadening it.

## Rollback readiness

Immediate rollback artifacts remain available:

- current API hotfix #137 deployment `dpl_GcmK9zYkGoy86mxwyq1X2NSC54ux` — **READY** at `9ea97b3184d155ed954cdf9d5f95e2a289e95a8e`;
- previous API hotfix #134 deployment `dpl_2bE5DEjCQtE2xDBgSnojAsuZKEdo` — **READY** at `389ef2ab17999db23abd7f4a77ea616b7ba5252b`;
- earlier API hotfix #131 deployment `dpl_7Pk1j3oBe3YvgcbRunP9JF8yBzVZ` — **READY** at `23678383a0a97dfc3df4feadecba507eb290f6ae`;
- earlier API Wave 3 deployment `dpl_q56DQQZgB6CBoSp8Bh9R5hCPrphr` — **READY** at `cbe7a967e37b90e4254fe838aff831eafe33536b`;
- pre-hotfix client deployment `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka` remains available at `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- current client deployment `dpl_CKmaLXMvrcjBgxo2zum6mQthtDnj` remains the verified production client artifact.

Database rollback continues to preserve the forward-compatible Project/lineage/worker-recovery schema rather than destructively removing migration history.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — records the bounded standing single-user Parallax production-promotion authority and automatic expiry condition;
- `ARCHITECTURE.md` v2.7 — updated for the permanent encoded Connect wire contract and production-only provider pre-cutover verification boundary;
- `DESIGN-SYSTEM.md` v2.1 — unchanged;
- `CURRENT-STATE.md` — updated for deployment-verified hotfix #137 and resolved production regression #136.

## Current decision

Wave 3 plus production hotfixes #125, #131, #134, and #137 are **PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED** at their affected infrastructure, persistence, provider, security, and release boundaries.

Production regression #136 is **RESOLVED / PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED**. Future validated Parallax releases may continue to use the standing single-user promotion authority without a separate approval request until the authority expires or is revoked.

The user is not the primary production test harness. Release automation and production evidence should reproduce and close ordinary implementation/provider/runtime defects; user involvement should be reserved for normal product use, genuine ambiguity, authority boundaries, or experience-level judgments that cannot be established from system evidence.

Wave 4 product UX and operating efficiency remains the next planned product phase.