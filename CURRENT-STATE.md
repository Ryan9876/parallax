# Parallax 2.0 Current State

Date: 2026-09-08
Status: **P2-V0.24.0 PRODUCTION-DEPLOYMENT-VERIFIED / PRODUCTION-ACCEPTANCE-PENDING**
Architecture: `ARCHITECTURE.md` v3.60

## Purpose of this record

This file is the authoritative snapshot of Parallax's current validated state. It records current production truth, active authority boundaries, the latest accepted release, and material remaining work. Historical evidence remains in Git history, versioned specifications, compiled plans, pull requests, workflow runs, deployment records, and workstream issues.

## P2-V0.24.0 — platform overhaul — PRODUCTION-DEPLOYMENT-VERIFIED / PRODUCTION-ACCEPTANCE-PENDING

- workstream: #601;
- release PR: #602;
- exact application merge: `06deab55e1a05585d8f76b224d3cec63a0b60f50`;
- validated candidate source before merge: `78c90bfbe8adccd1cbfb21a7536f310285e2c139`;
- exact starting baseline: `7b503876d3e2d9d42261235ff466f89432f37d5f` / P2-V0.23.50;
- architecture: v3.60;
- merge state: **merged to main** on 2026-09-08;
- deployment state: **production-deployment-verified**;
- production acceptance: **pending an authenticated real product-path acceptance proof**; infrastructure health and deterministic gates are not being treated as equivalent to full product acceptance.

P2-V0.24.0 modernizes the existing FastAPI/SQLAlchemy + Expo/React/Skia platform in place. It does not introduce the competing greenfield Next.js shell and does not change conversation-primary product hierarchy, Project/Work Specification/Engineering Run authority, exact source-lineage authority, worker lease/recovery semantics, Preview-only delivery ceiling, or human REVIEW completion authority.

Validated implementation:

1. core ORM definitions are organized under one compatibility-preserving `parallax_api.models` package sharing the existing `Base.metadata` graph; worker execution schema is no longer defined inside its repository;
2. additive composite indexes target demonstrated Engineering Run/history/event reads, and Engineering Run/event persistence removes redundant post-commit reloads without weakening durable commit, revision, attempt, event or lease semantics;
3. `SafeImplementationEngine.prepare()` is a pure immutable pre-mutation boundary, and `BoundedDerivedCache` is TTL/LRU derived-data acceleration only with no persistence, lifecycle, lease, lineage, credential or provider authority;
4. deterministic offline specification compilation is available for provider-independent development/regression use but records `dspy_run.executed=false`; authentic DSPy evidence and protected deterministic evaluation remain required for release;
5. the existing exact VERIFY-bound source-only / Vercel Preview delivery stack remains authoritative and is regression-gated for exact lineage, replay, stale/unverified rejection, fixed provider actions, no merge/production authority and no Engineering Run lifecycle mutation from delivery;
6. authenticated replayable SSE remains the preferred observability transport; the client adds bounded canonical REST reconciliation after stream failure, rejects non-advancing pages, deduplicates by durable sequence and treats its cursor as observation state only.

Validation and deployment evidence:

- P2-V0.24.0 Release Validation workflow `34240080110`: **SUCCESS**;
- release evidence artifact `10061591299`, digest `sha256:150fd5fcca70ee18e66715093b4a5edc16aa5fc5097135353864e0c4b0f9128f`;
- focused API authority/regression slice: **51 passed**;
- additive SQLite schema probe: **PASS**, existing sentinel data preserved;
- additive PostgreSQL 16 schema probe: **PASS**, existing sentinel data preserved;
- controlled transition benchmark against the exact P2-V0.23.50 `record()` path: baseline median `0.397272s` / `192` SQL statements versus candidate median `0.193603s` / `96` statements; measured latency improvement `51.27%`, statement reduction `50.0%`, both above the required `40%` gate. This is a controlled round-trip benchmark, not a claim of production request latency;
- pre-merge P2 CI `34240240010`: **SUCCESS**, including protected promotion evaluation and DSPy evidence validation;
- post-merge main P2 CI `34241209279`: **SUCCESS**, including Fast API + contract checks, Fast client checks, fresh DSPy SpecCritic/SpecCompiler promotion-boundary compilation, and Protected promotion evaluation;
- post-merge Workstream Spec Validation `34241209297`: **SUCCESS**;
- post-merge Client Visual Validation `34241209257`: **SUCCESS**;
- API production deployment: `dpl_hyFQJRQ5sN8AyiKP5Zjj2bveNHks`, exact source `06deab55e1a05585d8f76b224d3cec63a0b60f50`, **READY**;
- API canonical alias: `parallax-api-tan.vercel.app`;
- API `/health`: HTTP 200 / `{"status":"ok","service":"parallax-api","version":"0.1.0"}`;
- API `/ready`: HTTP 200 / `ready`, database `ok`, providers `ok`, provider target count `1`;
- API exact-deployment runtime logs confirm GET `/health` 200 and GET `/ready` 200 after cutover;
- client production deployment: `dpl_HFmjw42dU989cMwVsBT3gEHvJdQk`, exact source `06deab55e1a05585d8f76b224d3cec63a0b60f50`, **READY**;
- client canonical alias remains `parallax-lew7.vercel.app`;
- Vercel post-cutover runtime error clusters: **none found** for either API or client in the bounded verification window.

Production deployment build preflights passed on the exact application merge for provider registration, exact repository-scoped delivery permission, projected source, private Blob read/write, durable lineage composition, agentic runtime, projected bootstrap, execution snapshots, static-web candidate validation, Engineering Run event schema, and Behavioral Verification Plan schema before Vercel admitted the API deployment.

Authoritative-record impact:

- `ARCHITECTURE.md` is v3.60 for modular persistence, transition hot-path behavior, pure implementation/cache boundaries, offline-intelligence separation and bounded observability reconciliation;
- `DESIGN-SYSTEM.md` remains unchanged because the established Warm Editorial Observatory hierarchy, visual language, scrolling and accessibility rules are unchanged;
- `PROJECT-CONSTITUTION.md` remains unchanged because no durable governance or authority ceiling changed;
- this `CURRENT-STATE.md` update records the confirmed merge and deployment-verification evidence. It deliberately does not claim full production acceptance without an authenticated real product-path acceptance proof.

## Current production truth

### API

Current deployment-verified production API release:

- active production release: `P2-V0.24.0`;
- latest fully production-accepted baseline: `P2-V0.23.48`;
- P2-V0.24.0 release source: `06deab55e1a05585d8f76b224d3cec63a0b60f50`;
- production deployment: `dpl_hyFQJRQ5sN8AyiKP5Zjj2bveNHks`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- deployment state: `READY`;
- `/health`: HTTP 200 / `ok`;
- `/ready`: HTTP 200 / `ready`, database `ok`, providers `ok`, provider target count 1;
- unauthenticated REVIEW delivery-status route: HTTP 401 / `Authentication required`;
- post-cutover API runtime-error scan: clean.

The exact P2-V0.24.0 production API build passed production provider registration, exact repository-scoped delivery permission, projected-source, private Blob read/write, durable lineage composition, agentic runtime, projected bootstrap, execution-snapshot, static-web candidate-validation, Engineering Run event-schema, and Behavioral Verification Plan schema preflights before Vercel admitted the deployment.

Exact-head pre-merge and post-merge gates passed, including Workstream Spec Validation, protected compiled-plan validation, Bounded Autonomy, API regression, client checks, DSPy release compilation, protected promotion evaluation, cross-database schema probes, the transition-performance gate, and Browser/Skia acceptance. P2-V0.24.0 post-merge main workflow evidence: P2 CI `34241209279`, Workstream Spec Validation `34241209297`, Client Visual Validation `34241209257` — all SUCCESS.

P2-V0.24.0 is production-deployment-verified but is not yet recorded as fully production-accepted because this record has no authenticated real product-path acceptance proof for the overhaul. Separately, the OT Time REVIEW delivery retry introduced in P2-V0.23.50 remains an explicit operator action. Until a trusted authenticated acceptance run succeeds, P2-V0.23.48 remains the latest fully production-accepted baseline.

### Client

Current deployment-verified production client release:

- release: `P2-V0.24.0`;
- source: `06deab55e1a05585d8f76b224d3cec63a0b60f50`;
- production deployment: `dpl_HFmjw42dU989cMwVsBT3gEHvJdQk`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- canonical user URL: `https://parallax-lew7.vercel.app`;
- deployment state: `READY`;
- post-cutover client runtime-error scan: clean.

P2-V0.24.0 preserves the P2-V0.23.50 user-visible corrections and adds bounded canonical observability reconciliation without changing the established visual language:

1. an explicit REVIEW delivery panel that reads canonical delivery status and exposes `Retry Vercel Preview` only when the exact verified lineage has not been published;
2. a vertically scrollable desktop Live Build root while dense event/code/evidence panes retain bounded nested scrolling and mobile behavior remains unchanged.

Successful delivery status exposes only bounded safe `Open Vercel Preview` and `Open GitHub PR` actions and explicitly does not imply merge or production deployment.

### Execution and authority

Parallax retains governed Python, .NET, and marker-free `static-web-v1` execution. Candidate source cannot select commands, execution snapshots, provider credentials, source lineage, Git publication authority, Vercel Preview authority, lifecycle transitions, merge, default-branch application publication, or production promotion.

Human `REVIEW` remains the completion boundary. The accepted source-delivery recovery chain does not authorize automatic review completion, PR merge, default-branch mutation, or production promotion.

## OT Time production recovery — explicit operator retry pending

Production Engineering Run:

- run: `89f6db3f-7a56-4e18-8307-22e377b2766a`;
- conversation: `8a444a1c-f60d-47d7-b02d-634cacf00596`;
- Project: `9e898865-b98e-41d3-b000-bdc87bad377f`;
- repository: `github:Ryan9876/ot-time`;
- delivery mode: `vercel-preview`;
- state: `REVIEW`;
- revision: `6`;
- `last_failure_code=null`;
- protected PLAN/IMPLEMENT/BUILD/TEST/VERIFY attempts: 5, all preserved;
- exact accepted and VERIFY-bound lineage: `src:cbc1721069780eb6ced2545d9a649f9e722caee0ce24d3775e0356e4d2051609`;
- durable `SOURCE_DELIVERY` records before the P2-V0.23.50 retry: 0.

The earlier autonomous request reached human REVIEW after IMPLEMENT, BUILD, TEST and VERIFY passed, but Vercel Preview readiness failed and emitted bounded `SOURCE_DELIVERY_FAILED` observation. That provider failure did not change protected run state or `last_failure_code`.

P2-V0.23.50 now provides an explicit delivery-only recovery boundary. A retry:

- requires exact REVIEW and the current run revision;
- derives Project, repository, accepted lineage, branch, commit, pull request, Vercel Project and deployment identities on the server;
- reuses the exact accepted IMPLEMENT + passed VERIFY lineage and current durable lineage head;
- invokes only the existing replay-safe GitHub/Vercel delivery stack;
- never reruns PLAN, IMPLEMENT, BUILD, TEST or VERIFY;
- cannot merge a PR, publish to the production branch, complete REVIEW automatically, or authorize production promotion;
- must preserve run state, revision, protected attempts, accepted lineage and `last_failure_code` on both success and failure.

The remaining acceptance action is intentionally human-triggered: refresh the production client, return to the REVIEW delivery panel, and choose `Retry Vercel Preview`. Production acceptance of this recovery path requires provider and database read-back after that explicit action.

## P2-V0.23.50 — REVIEW delivery recovery + desktop observability reachability — PRODUCTION-DEPLOYMENT-VERIFIED

- workstream: #597;
- release PR: #598;
- merge source: `945ba43c4f3f465a04792d7832a422b58f89d999`;
- Architecture: v3.59;
- API deployment: `dpl_6NHLUEiNhUpkFczVekyyPmZqxGuT`, READY;
- client deployment: `dpl_Dc7oLFBpF3MTKAxeXM8sa5qigK77`, READY;
- main P2 CI: `34189149239` — SUCCESS;
- main Workstream Spec Validation: `34189149255` — SUCCESS;
- main Client Visual Validation: `34189149237` — SUCCESS.

P2-V0.23.50 introduces a read-only REVIEW delivery-status API plus a REVIEW-only delivery-retry API. Retry uses the existing exact verified-lineage delivery contract directly rather than generic autonomous continuation. A successful retry may add/replay only the established `SOURCE_DELIVERY` durable record and bounded delivery event; protected lifecycle authority remains unchanged.

The same release corrects desktop Run observability reachability. The workspace now owns an outer vertical scroll at desktop widths, while the Run Event Stream and other dense inspection panes retain bounded nested scroll behavior. Compact/mobile root scrolling remains unchanged.

P2-V0.23.49, merge source `386a9a526b1bf3a12d9aafe65068660acc135b86`, remains the immediately preceding autonomy single-flight foundation: an unexpired active worker lease is treated as active concurrency and mapped to bounded `AUTONOMY_IN_PROGRESS` instead of durable IMPLEMENT failure. P2-V0.23.50 preserves that behavior.

## Frozen W9-S1 — current validated position

Engineering Run:

- run: `a64d56b7-ad42-42ad-9562-891783363f4a`;
- project: `0e20392b-debc-4a86-80e8-dd87c57cf510`;
- state: `REVIEW`;
- revision: `12`;
- `last_failure_code=null`;
- reviewed base lineage: `src:da5d0fb62d34a3228bb56e7a7d82971c8023a536d11944ba71bcaa51a407b871`;
- replacement accepted lineage: `src:001736ab731e243956cf78ede7a0087d2b81595f1008568850eac1e9acc3e809`;
- replacement content digest: `9c0971c7d1d2fbc483e793a34e97bd0a865790592a796c4beefde0effeaa43d9`.

The P2-V0.23.41 bounded REVIEW correction cycle remains valid: the same run accepted the replacement lineage, BUILD/TEST/VERIFY passed, and the run returned to human REVIEW revision 12 without widening the immutable Work Specification or falsely converting structural-only evidence into behavioral acceptance.

### Replacement source delivery — accepted

Frozen production acceptance workflow:

- QA repository: `Ryan9876/parallax-qa`;
- workflow: `.github/workflows/production-replay.yml`;
- acceptance run: `33815162497`;
- acceptance job: `100845569723`;
- result: **SUCCESS**;
- autonomous result: `REVIEW_REQUIRED`;
- post-acceptance run state: `REVIEW` revision 12, `last_failure_code=null`.

Exact replacement publication evidence:

- branch: `parallax/0e20392b-a64d56b7-001736ab731e243956cf78ede7a0087d2b81595f1008568850eac1e9acc3e809`;
- reused exact partial lineage commit: `54d2d28880e1cfdcaf9632bb342049821a5a6be1`;
- GitHub replacement PR: `Ryan9876/parallax-qa1#2`, OPEN;
- PR #2 base: `main` at `b24c029be916f8b1f0ab07347a988f814cc8d567`;
- Vercel Preview: `dpl_8vMWNKDemTjqkUTZ3Uei3zAV8pUt`;
- Preview state: `READY`;
- durable `SOURCE_DELIVERY`: stage attempt 2, `RECORDED`;
- durable run event: sequence 32, `SOURCE_DELIVERY`, outcome `SUCCEEDED`, subsystem `VERCEL`;
- delivery action count: 6.

The successful delivery performed bounded repository inspection, exact lineage commit replay, PR create/read, and Preview create/read. No branch reset, deletion, force update, alternate branch, merge, default-branch mutation, or production promotion occurred.

### Historical publication remains untouched

The earlier reviewed lineage remains preserved exactly:

- historical branch: `parallax/0e20392b-a64d56b7`;
- historical branch head: `ee945138e84972d6b635b9e9a086e625ef19fccb`;
- historical GitHub PR: `Ryan9876/parallax-qa1#1`, OPEN;
- PR #1 remains unmerged and its exact head is unchanged.

Independent provider read-back after acceptance confirmed both the replacement branch/PR and historical branch/PR identities. The replacement Preview independently read back as READY in Vercel project `prj_g4XtKZIenAj0OB01nCN3JDDMAPdM`.

## P2-V0.23.48 — conservative Behavioral Verification Plan normalization — PRODUCTION-ACCEPTED

- workstream: #592;
- release PR: #593;
- merge source: `925774ed35af0a0f66c9199626952f59f18c3ed9`;
- API deployment: `dpl_ENo6k67tBwtk5GdH7tFfGsAY5zWS`, READY;
- Architecture: v3.57;
- trusted production acceptance: `34176835861` / job `101907806487` — SUCCESS;
- QA harness correction PR: `Ryan9876/parallax-qa#5`;
- trusted QA main source for the successful replay: `746987b02c8d8fbeb12301c95045ce7f17ac7bbb`.

Authenticated P2-V0.23.47 acceptance initially exposed a product robustness defect: a model-proposed `BROWSER` criterion that violated the closed browser contract caused the whole proposal to fail and escalated through the model route. P2-V0.23.48 preserves exact acceptance identity but moves executable failure to the criterion boundary. A valid BROWSER proposal remains unchanged; an invalid executable BROWSER proposal is not repaired and instead becomes `HUMAN_ONLY` with no executable authority. Explicit HUMAN_ONLY proposals likewise discard executable fields.

Malformed top-level structure, unknown modes, missing/duplicated/invented/reordered acceptance IDs, and other identity failures remain whole-proposal protected-validation failures. Provider-successful malformed output is classified through the existing structured-output validation boundary, while real transport, timeout, and rate-limit failures remain provider failures.

The fixed browser vocabulary now exposes action-specific required/forbidden fields and directs generation to choose HUMAN_ONLY rather than guess. Raw model output remains non-durable. Only the normalized strict proposal may compile, digest, persist, and enter explicit operator approval.

Production acceptance proved the conservative outcome on the frozen W9-S1 Work Specification: Luna produced a valid normalized plan covering all six server-derived criteria as HUMAN_ONLY. Revision 2 was explicitly approved and replay-approved; no browser execution occurred and no behavioral criterion was converted into verified evidence.

The first post-deployment trusted replay after the P2-V0.23.48 fix successfully created plan revision 1 but the QA harness then failed its independent digest assertion because `jq -cS` added a trailing newline before `sha256sum`. Database verification proved the persisted canonical digest was correct. QA PR #5 changed only the independent check to `jq -cSj`, preserving the trusted workflow identity and OIDC audience. The subsequent fresh trusted replay passed end to end.

## P2-V0.23.47 — durable Behavioral Verification Plan foundation — SUPERSEDED BY P2-V0.23.48

- workstream: #589;
- release PR: #590;
- merge source: `8fda8a96a0093dcfa12e10b85608f636c430ee30`;
- API deployment: `dpl_ANkAiZi7oSH4QcqWcvaTmJ2zLeip`, READY;
- client deployment: `dpl_7xe6W6bcFiSyzP8GeEGSxoqb8kGu`, READY;
- Architecture: v3.56;
- Supabase migration: `20260908003104_behavioral_verification_plans`;
- production database project: `kjyenifnfjqnzfgshpwg`.

P2-V0.23.47 established the separately versioned Behavioral Verification Plan artifact, exact Work Specification binding, canonical plan digest, `BROWSER | HUMAN_ONLY` partition, additive persistence, owner-scoped read/draft/approve API, explicit replay-safe approval, and Build Plan review UI. It deliberately added no browser execution or behavioral acceptance-proof authority.

Its production deployment and schema admission were valid. The authenticated acceptance attempt exposed the generator robustness issue corrected by P2-V0.23.48; therefore P2-V0.23.47 remains the architectural/persistence foundation rather than the current production-accepted release.

## P2-V0.23.42 through P2-V0.23.46 — source-publication recovery chain

The W9-S1 replacement-publication blocker was resolved through five separately governed, fail-closed releases. Each release kept the Engineering Run at human REVIEW and used production evidence from the previous release to narrow the next correction.

### P2-V0.23.42 — commit-bearing empty repository compatibility

- workstream: #570;
- release PR: #579;
- merge source: `9e169ac707126c078195c75403e2d7c58bae1dec`;
- production deployment: `dpl_64w1FdF7jGbfCKYbuxJQamoNqSz5`, READY;
- Architecture: v3.51.

P2-V0.23.42 distinguished a truly empty repository from an ordinary commit-bearing default branch whose exact tree is the universal Git empty tree. The latter can be used directly as the bounded feature-branch base without rewriting or reinitializing the default branch.

Production replay then exposed that replacement publication identity was still only Project+Run scoped and collided with the previously delivered lineage.

### P2-V0.23.43 — lineage-scoped publication and durable delivery identity

- workstream: #580;
- release PR: #581;
- merge source: `f96a865bb8d97d0e85574246ffa673de50d18b35`;
- production deployment: `dpl_BvbYZx2jrcRWrGbecBP35UVryxq6`, READY;
- Architecture: v3.52.

P2-V0.23.43 made provider branch identity exact-lineage scoped and allowed multiple distinct `SOURCE_DELIVERY` attempts within the same Engineering Run while preserving exact-lineage replay.

Production acceptance proved the replacement branch identity was correct, but also exposed real provider partial-publication behavior:

1. GitHub returned 201 for exact branch creation, followed by an immediate 404 on the new ref;
2. a later retry created the exact lineage tree/commit and PATCHed the branch, followed by a stale read that caused `SOURCE_MISMATCH`;
3. the branch was therefore left at the exact partial commit, and the next retry failed `BRANCH_CONFLICT` before exact commit replay could be considered.

No historical branch/PR mutation occurred.

### P2-V0.23.44 — bounded exact partial-publication recovery

- workstream: #582;
- release PR: #583;
- merge source: `be367408e8878e5a896be5ea437e401ff7ca2e0f`;
- production deployment: `dpl_GiF9VzzX1fVcE5VmJ8csBH9B5gvc`, READY;
- Architecture: v3.53.

P2-V0.23.44 added one-shot exact Git ref mutation acknowledgement for immediate provider read-after-write inconsistency and allowed a canonical advanced lineage branch to resume only through deterministic exact-lineage replay proof. Arbitrary/mismatched branch heads remained conflicts.

Production replay reached the stronger proof path but revealed an implementation defect: recursive tree verification passed commit SHAs directly to GitHub's Trees API, causing bounded `SOURCE_NOT_FOUND`.

### P2-V0.23.45 — exact commit-to-tree identity replay

- workstream: #584;
- release PR: #585;
- merge source: `4c9214cc92abb40a4480a63cbbe65a23d676605b`;
- production deployment: `dpl_495A2xerRjExmsWqwyP43Jtk7YSx`, READY;
- Architecture: v3.54.

P2-V0.23.45 corrected replay verification to resolve exact parent and candidate commit objects to their validated `tree.sha` identities before recursive tree comparison. Forged tree deltas and malformed tree identities remained fail-closed.

Production replay then reached the exact parent tree and exposed the already-known GitHub canonical-empty-tree behavior: the verified parent commit referenced `4b825dc642cb6eb9a060e54bf8d69288fbee4904`, while GitHub returned 404 when asked to materialize that universal empty-tree object directly.

### P2-V0.23.46 — canonical empty-tree replay compatibility — PRODUCTION-ACCEPTED

- workstream: #586;
- release PR: #587;
- merge source: `a267364022fc3742e642ccb1bfc432480190785d`;
- production deployment: `dpl_6WSxLp2R21fgjP4W7CWfs3r7NF3R`, READY;
- Architecture: v3.55;
- full pre-PR API regression: 1267 passed, 1 skipped;
- exact-head protected Bounded Autonomy, Workstream Spec Validation, and P2 CI: SUCCESS;
- post-merge Workstream Spec Validation and P2 CI: SUCCESS;
- frozen W9-S1 production acceptance: `33815162497` / job `100845569723` — SUCCESS.

P2-V0.23.46 reuses the pre-existing Architecture v3.48 provider-compatibility rule: only the exact universal Git empty-tree SHA may produce an empty snapshot without a Trees GET. Every non-canonical tree still requires normal provider verification and a missing non-canonical tree still fails `SOURCE_NOT_FOUND`.

This completed the replacement source-publication recovery without weakening v3.53/v3.54 lineage, parent, changed-path, mode, byte-size, content-digest, provider, Preview, or human REVIEW boundaries.

## QA trust state

The standing production-QA identity is intentionally bounded to:

- repository: `Ryan9876/parallax-qa`;
- workflow: `.github/workflows/production-replay.yml@refs/heads/main`;
- audience: `parallax://qa-production`;
- workflow permissions: `contents: read`, `id-token: write`;
- current trusted workflow blob: `9b3560124ddcefb247916aca2d3d73e6c7fedc12`.

The workflow obtains the short-lived OIDC token through GitHub's supported `core.getIDToken('parallax://qa-production')` path, masks it, writes it only to an ephemeral mode-0600 runner file, exchanges it through `/v1/session/qa-automation`, and then uses the normal authenticated session cookie. No raw long-lived credential was introduced.

QA PR #5 corrected only the canonical digest assertion in `scripts/p02347_behavioral_plan_acceptance.sh`; it did not alter the credential-bearing workflow, audience, trust list, or application auth boundary. The merge source is `746987b02c8d8fbeb12301c95045ce7f17ac7bbb`.

Post-merge QA Harness CI `34176835888` succeeded. Trusted production replay `34176835861` then succeeded end to end.

## Active governed work

P2-V0.24.0 is the active production deployment and is deployment-verified. P2-V0.23.48 remains the current fully production-accepted release until an authenticated real product-path acceptance proof is recorded.

The frozen W9-S1 replacement candidate remains available for human REVIEW. The Engineering Run is still `REVIEW` revision 12, and no source-publication blocker remains.

Static-web TEST/VERIFY remains explicitly structural-only for the six protected acceptance criteria: `acceptance_ids_verified=[]`. The approved Behavioral Verification Plan now provides a separately governed mapping artifact, but all six current entries are HUMAN_ONLY and therefore do not alter behavioral acceptance evidence.

The next behavioral-verification slice may compose protected browser execution only through a separately approved specification and the existing closed browser contract. P2-V0.23.48 itself authorizes no browser execution.

No automatic REVIEW completion, PR merge, default-branch application publication, or production promotion is authorized.

## Authoritative-record reconciliation

- `CURRENT-STATE.md`: updated because P2-V0.23.48 is merged, exact-source production deployment `dpl_ENo6k67tBwtk5GdH7tFfGsAY5zWS` is READY, health/readiness and runtime scans are clean, and authenticated production acceptance `34176835861` succeeded with immutable Work Specification/run/event evidence.
- `ARCHITECTURE.md`: v3.57 is authoritative because conservative generated-proposal normalization is now part of the durable behavioral-plan authority boundary.
- `DESIGN-SYSTEM.md`: unchanged by P2-V0.23.48; no product-surface semantics changed beyond the already-recorded P2-V0.23.47 Build Plan review UI.
- `PROJECT-CONSTITUTION.md`: unchanged; least privilege, fail-closed provider trust, explicit human control, and human REVIEW authority remain intact.
