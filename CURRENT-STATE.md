# Parallax 2.0 Current State

Date: 2026-09-07
Status: **P2-V0.23.48 PRODUCTION-ACCEPTED / W9-S1 HUMAN REVIEW REQUIRED**
Architecture: `ARCHITECTURE.md` v3.57

## Purpose of this record

This file is the authoritative snapshot of Parallax's current validated state. It records current production truth, active authority boundaries, the latest accepted release, and material remaining work. Historical evidence remains in Git history, versioned specifications, compiled plans, pull requests, workflow runs, deployment records, and workstream issues.

## Current production truth

### API

Current deployment-verified production API release:

- release: `P2-V0.23.48`;
- latest fully production-accepted baseline: `P2-V0.23.48`;
- release source: `925774ed35af0a0f66c9199626952f59f18c3ed9`;
- production acceptance deployment: `dpl_ENo6k67tBwtk5GdH7tFfGsAY5zWS`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- deployment state: `READY`;
- `/health`: HTTP 200 / `ok`;
- `/ready`: HTTP 200 / `ready`, database `ok`, providers `ok`;
- post-cutover runtime-error scan: clean.

The exact P2-V0.23.48 production build passed provider registration, exact repository-scoped delivery permission, projected-source, private Blob read/write, lineage composition, agentic runtime, projected bootstrap, execution-snapshot, static-web candidate-validation, Engineering Run event-schema, and Behavioral Verification Plan schema preflights. The Behavioral Verification Plan schema guard explicitly confirmed `behavioral_verification_plans` before deployment admission.

Pre-merge exact-head Workstream Spec Validation, P2 CI, Bounded Autonomy, DSPy release compilation, protected promotion evaluation, API regression, and client checks passed. Post-merge main-branch Workstream Spec Validation and P2 CI also completed successfully on the exact merged source.

Authenticated production acceptance succeeded through the trusted QA identity:

- QA repository: `Ryan9876/parallax-qa`;
- trusted workflow: `.github/workflows/production-replay.yml@refs/heads/main`;
- audience: `parallax://qa-production`;
- acceptance run: `34176835861`;
- acceptance job: `101907806487`;
- result: **SUCCESS**;
- Work Specification: `6b24646e-79a8-4548-84d4-c5e6340de659`, revision 1, unchanged;
- Engineering Run: `a64d56b7-ad42-42ad-9562-891783363f4a`, `REVIEW` revision 12, `last_failure_code=null`, unchanged;
- approved Behavioral Verification Plan: `065879d7-300d-4b4f-941e-55b581d7dc45`, revision 2;
- plan status: `APPROVED`;
- plan digest: `0da28c23f0b92baecb3f15fe34bad6971c5f50029bb59e555731c1df68bc6544`;
- generator: `behavioral-verification-plan-v0.23.48` / `openai/gpt-5.6-luna`;
- acceptance coverage: 6/6 exact server-derived criteria;
- approved plan classification: all six criteria `HUMAN_ONLY`; no executable browser workflow was admitted;
- repeated approval: replay-safe / HTTP 200.

Independent replay evidence proved the frozen artifacts were unchanged:

- Work Specification response hash: `193ad7941ba27fe2ef49a2513160156040053e18194eb352810271df134d6b65`;
- Engineering Run response hash: `d65c074da84356cb6c80584eb395b37bdf620f64606d012b04c1f80e9935d265`;
- Engineering Run events response hash: `5dbd3c036ad9ef30ce3e008b76d92b7c878929f5a57c615533859537d062265a`;
- approval replay hash: `49b205ff3497d0484c4728c4c63195ccdeaed82c54a217f2ce143c3fd6ee97f4`.

Database read-back confirmed revision 1 of the plan is `SUPERSEDED`, revision 2 is `APPROVED`, the Work Specification remains `APPROVED` revision 1, and the Engineering Run remains `REVIEW` revision 12. Durable run-event state remains 32 events with maximum sequence 32.

### Client

P2-V0.23.48 is an API behavioral-plan generation correction and introduces no client-code change. The production client remains the P2-V0.23.47 Build Plan UI release:

- client source: `8fda8a96a0093dcfa12e10b85608f636c430ee30`;
- production deployment: `dpl_7xe6W6bcFiSyzP8GeEGSxoqb8kGu`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- deployment state: `READY`;
- post-cutover runtime-error scan for that client release: clean.

The Build Plan continues to expose the separately governed Behavioral Verification Plan review surface. UI wording distinguishes `Automated browser check` from `Human review` and does not claim that an approved verification plan is behavioral acceptance evidence.

### Execution and authority

Parallax retains governed Python, .NET, and marker-free `static-web-v1` execution. Candidate source cannot select commands, execution snapshots, provider credentials, source lineage, Git publication authority, Vercel Preview authority, lifecycle transitions, merge, default-branch application publication, or production promotion.

Human `REVIEW` remains the completion boundary. The accepted source-delivery recovery chain does not authorize automatic review completion, PR merge, default-branch mutation, or production promotion.

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

P2-V0.23.48 is the current fully production-accepted release.

The frozen W9-S1 replacement candidate remains available for human REVIEW. The Engineering Run is still `REVIEW` revision 12, and no source-publication blocker remains.

Static-web TEST/VERIFY remains explicitly structural-only for the six protected acceptance criteria: `acceptance_ids_verified=[]`. The approved Behavioral Verification Plan now provides a separately governed mapping artifact, but all six current entries are HUMAN_ONLY and therefore do not alter behavioral acceptance evidence.

The next behavioral-verification slice may compose protected browser execution only through a separately approved specification and the existing closed browser contract. P2-V0.23.48 itself authorizes no browser execution.

No automatic REVIEW completion, PR merge, default-branch application publication, or production promotion is authorized.

## Authoritative-record reconciliation

- `CURRENT-STATE.md`: updated because P2-V0.23.48 is merged, exact-source production deployment `dpl_ENo6k67tBwtk5GdH7tFfGsAY5zWS` is READY, health/readiness and runtime scans are clean, and authenticated production acceptance `34176835861` succeeded with immutable Work Specification/run/event evidence.
- `ARCHITECTURE.md`: v3.57 is authoritative because conservative generated-proposal normalization is now part of the durable behavioral-plan authority boundary.
- `DESIGN-SYSTEM.md`: unchanged by P2-V0.23.48; no product-surface semantics changed beyond the already-recorded P2-V0.23.47 Build Plan review UI.
- `PROJECT-CONSTITUTION.md`: unchanged; least privilege, fail-closed provider trust, explicit human control, and human REVIEW authority remain intact.
