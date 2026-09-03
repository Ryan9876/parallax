# Parallax 2.0 Current State

Date: 2026-09-03
Status: **P2-V0.23.46 PRODUCTION-ACCEPTED / W9-S1 REPLACEMENT SOURCE DELIVERY PROVEN / HUMAN REVIEW REQUIRED**
Architecture: `ARCHITECTURE.md` v3.55

## Purpose of this record

This file is the authoritative snapshot of Parallax's current validated state. It records current production truth, active authority boundaries, the latest accepted release, and material remaining work. Historical evidence remains in Git history, versioned specifications, compiled plans, pull requests, workflow runs, deployment records, and workstream issues.

## Current production truth

### API

Current deployment-verified production API source:

- release: `P2-V0.23.46`;
- source: `a267364022fc3742e642ccb1bfc432480190785d`;
- production deployment: `dpl_6WSxLp2R21fgjP4W7CWfs3r7NF3R`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- deployment state: `READY`;
- `/health`: HTTP 200 / `ok`, independently required by the successful frozen production-acceptance workflow;
- `/ready`: HTTP 200 / `ready`, database `ok`, providers `ok`.

The exact P2-V0.23.46 production build passed provider registration, exact repository-scoped delivery permission, projected-source, private Blob read/write, lineage composition, agentic runtime, projected bootstrap, execution snapshot, static-web candidate validation, and Engineering Run event-schema preflights. The exact-deployment pre-acceptance error/warning/fatal runtime scan was clean.

Post-merge Workstream Spec Validation and P2 CI completed successfully on the exact merged source.

### Client

The production client remains the previously accepted P2-V0.23.41 client because P2-V0.23.42 through P2-V0.23.46 are API/provider-delivery releases and do not change client behavior:

- source: `78b408a2323ab474c3183a64d55c6399f5b20402`;
- production deployment: `dpl_9u4GGmpLW8xzhdDZnVARStxLtmSj`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- deployment state: `READY`.

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

The temporary P2-V0.23.46 acceptance workflow was removed after evidence capture.

The standing production-QA workflow was restored byte-for-byte:

- restore commit: `1c2146efee33c3fa7b0473fe76a4bc8db9ec8074`;
- trusted workflow blob: `e1a619d44ed26075c0c97eb6cf0b5fa931c2c75f`;
- post-restore QA Harness CI: SUCCESS.

The standing production-replay workflow intentionally retains its older frozen assertion and may fail when pushed because W9-S1 is now revision 12 rather than its historical revision 6 expectation. That expected standing-harness result is not a product regression and does not alter the successful P2-V0.23.46 acceptance evidence above.

## Active governed work

The replacement candidate is now published and available for human REVIEW. No source-publication blocker remains on the frozen W9-S1 acceptance path.

The static-web TEST/VERIFY stages remain explicitly structural-only for the six protected acceptance criteria: `acceptance_ids_verified=[]`. A future browser/behavioral verifier that can produce governed behavioral evidence remains a separate capability and must not be inferred from source delivery or Preview readiness.

No automatic REVIEW completion, PR merge, default-branch application publication, or production promotion is authorized.

## Authoritative-record reconciliation

- `CURRENT-STATE.md`: updated because P2-V0.23.42 through P2-V0.23.46 are now fully reconciled, P2-V0.23.46 is exact-source deployment-verified and frozen-behavior accepted, and W9-S1 replacement GitHub/Vercel delivery is independently verified.
- `ARCHITECTURE.md`: authoritative at v3.55. v3.51 through v3.55 record the durable repository-state, lineage-publication, partial-recovery, commit/tree-identity, and canonical-empty-tree semantics.
- `DESIGN-SYSTEM.md`: unchanged; no durable visual-system rule changed.
- `PROJECT-CONSTITUTION.md`: unchanged; least privilege, fail-closed provider trust, explicit human control, and human REVIEW authority remain intact.
