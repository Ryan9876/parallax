# Parallax 2.0 Current State

Date: 2026-09-02
Status: **P2-V0.23.41 PRODUCTION-ACCEPTED / W9-S1 REVIEW CORRECTION CYCLE PROVEN / HUMAN REVIEW REQUIRED / SOURCE REPUBLICATION FOLLOW-UP ACTIVE**
Architecture: `ARCHITECTURE.md` v3.50

## Purpose of this record

This file is the authoritative snapshot of Parallax's current validated state. It records current production truth, active authority boundaries, the latest accepted release, and material remaining work. Historical evidence remains in Git history, versioned specifications, compiled plans, pull requests, workflow runs, deployment records, and workstream issues.

## Current production truth

### API

Current deployment-verified production API application source:

- source: `78b408a2323ab474c3183a64d55c6399f5b20402`;
- release: `P2-V0.23.41`;
- production deployment: `dpl_34wDWx1gSXFh4U4ZzEAizF7eBL8J`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- deployment state: `READY`;
- `/health`: HTTP 200 / `ok`;
- `/ready`: HTTP 200 / `ready`, database `ok`, providers `ok`.

The exact P2-V0.23.41 production build passed provider, exact delivery-permission, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot, static-web candidate-validation, and Engineering Run event-schema preflights. Pre-acceptance exact-deployment runtime scans showed no deployment-health errors. A later expected QA acceptance request produced one application-level `503` after the corrected run had already returned to REVIEW; that bounded source-publication condition is isolated below and tracked by P2-V0.23.42 rather than treated as an API deployment-health failure.

### Client

Current production client is the P2-V0.23.41 release:

- source: `78b408a2323ab474c3183a64d55c6399f5b20402`;
- production deployment: `dpl_9u4GGmpLW8xzhdDZnVARStxLtmSj`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- deployment state: `READY`.

The ordinary authenticated client now exposes bounded REVIEW rework on desktop/web and compact mobile. The production release was validated through the existing state/contract suite, TypeScript typecheck, web export, and real desktop + 390px browser interaction before merge.

### Execution and authority

Parallax retains the governed Python, .NET, and marker-free `static-web-v1` execution paths. Candidate source cannot select commands, execution snapshots, provider credentials, source lineage, Git publication, Preview authority, lifecycle transitions, merge, or production promotion.

Human `REVIEW` remains the completion boundary. P2-V0.23.41 adds only explicit, acceptance-linked correction control within an already-approved Work Specification. It does not authorize automatic REVIEW completion, merge, default-branch application publication, or production promotion.

## P2-V0.23.41 — bounded REVIEW rework — PRODUCTION-ACCEPTED

Workstream: #568  
Release PR: #569  
Governing specification: `specs/P2-V0.23.41.md`  
Architecture: v3.50

### Release evidence

- authentic DSPy spec/critic/compiler gate: `33683418256` — SUCCESS;
- focused backend implementation gate: `33684263586` — SUCCESS;
- final clean-head integrated gate: `33686282520` — SUCCESS, including 1243 API tests passed / 1 skipped, client state/REVIEW contract validation, typecheck, web export, and desktop/mobile browser rework smoke;
- exact validated release-branch head: `67478a6cd2e4b330e8ed057d7a04a52fc2fbb968`;
- PR #569 exact-head Bounded Autonomy, Workstream Spec Validation, P2 CI, and Client Visual Validation: SUCCESS;
- exact merge/application source: `78b408a2323ab474c3183a64d55c6399f5b20402`;
- post-merge P2 CI `33686895116`: SUCCESS, including fresh DSPy promotion compilation;
- post-merge Workstream Spec Validation `33686895040`: SUCCESS;
- post-merge Client Visual Validation `33686895073`: SUCCESS;
- exact API production deployment `dpl_34wDWx1gSXFh4U4ZzEAizF7eBL8J`: READY;
- exact client production deployment `dpl_9u4GGmpLW8xzhdDZnVARStxLtmSj`: READY.

### Frozen W9-S1 production acceptance

Read-only QA replay `33702872373` confirmed frozen Engineering Run `a64d56b7-ad42-42ad-9562-891783363f4a` at `REVIEW` revision 6 with the immutable approved acceptance map. The two concrete REVIEW findings bind exactly to:

- `AC-03`: safe export/import, including invalid import failing without corrupting valid persisted data;
- `AC-05`: automated quality coverage for core CRUD, persistence, search/filter, and import behavior.

Authenticated production rework run `33702978417` submitted only `AC-03` and `AC-05`. The bounded control operation transitioned the same run from REVIEW revision 6 to PLAN revision 7 and persisted rework attempt `8e665980-225d-40f3-abf5-44afa5edf10a`.

The fresh correction cycle then proved:

- durable event 17: explicit human REVIEW rework control recorded;
- durable event 18: prior `READY_FOR_INTEGRATION` selected candidate invalidated and worker re-armed through existing `RECOVERING` semantics;
- fresh PLAN bound base lineage `src:da5d0fb62d34a3228bb56e7a7d82971c8023a536d11944ba71bcaa51a407b871`;
- PLAN persisted deterministic rework-context digest `7fe021647a4e04e31623113d5facd1dc83186dcb805f54f2bd755049e0da8a7c` and exact affected IDs `[AC-03, AC-05]`;
- replacement IMPLEMENT accepted new immutable lineage `src:001736ab731e243956cf78ede7a0087d2b81595f1008568850eac1e9acc3e809`, with the reviewed lineage above as its exact base;
- BUILD, TEST, and VERIFY all passed on the replacement lineage;
- TEST and VERIFY preserved P2-V0.23.40 evidence truthfulness: `acceptance_ids_verified=[]` and all six protected criteria remain explicit unverified structural-only criteria;
- durable event 30 returned the same run to human `REVIEW` revision 12;
- post-cycle read `33703157321` confirmed `state=REVIEW`, `revision=12`, `binding_status=APPROVED_SPEC_BOUND`, and `last_failure_code=null`.

This satisfies the P2-V0.23.41 acceptance target: an authenticated operator can correct an exact REVIEW candidate within the immutable approved Work Specification, preserve same-run source continuity, regenerate through the normal protected lifecycle, and return to human REVIEW without widening authority.

## W9-S1 — current position

Frozen W9-S1 Engineering Run `a64d56b7-ad42-42ad-9562-891783363f4a` is now at `REVIEW` revision 12.

- reviewed base lineage: `src:da5d0fb62d34a3228bb56e7a7d82971c8023a536d11944ba71bcaa51a407b871`;
- replacement accepted lineage: `src:001736ab731e243956cf78ede7a0087d2b81595f1008568850eac1e9acc3e809`;
- human REVIEW remains required;
- the prior GitHub PR #1 / Vercel Preview still represent the earlier delivered lineage until the replacement lineage can be republished through the bounded source-delivery path.

After the corrected run had already returned to REVIEW, source republication failed bounded as durable event 31:

- provider: GitHub;
- action: `repository.initialize-empty`;
- result: `GREENFIELD_BASELINE_MISMATCH`;
- current run state remained REVIEW revision 12 with no run failure.

The target repository is no longer in the exact state used by the original W9 delivery. `Ryan9876/parallax-qa1/main` currently points to user-authored cleanup commit `b24c029be916f8b1f0ab07347a988f814cc8d567` with canonical empty tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904`. That commit was created during later P2-V0.23.40 QA cleanup and is not the exact Parallax two-commit greenfield baseline. The follow-up is tracked separately as #570 / P2-V0.23.42; history will not be rewritten and a temporary non-empty fixture will not be introduced merely to force acceptance.

The standing production-QA workflow was restored byte-for-byte to trusted blob `e1a619d44ed26075c0c97eb6cf0b5fa931c2c75f` after acceptance evidence was captured.

## Active governed work

### P2-V0.23.42 — commit-bearing empty repository delivery compatibility

Workstream: #570  
State: **SPEC-FIRST / semantic implementation blocked pending authentic DSPy gate**

The next bounded objective is to distinguish a truly empty repository with no usable default ref from a commit-bearing repository whose authenticated current head tree is empty. The former continues to require the strict Parallax greenfield initializer; the latter should use its exact authenticated head as the ordinary branch base without rewriting the default branch, if the specification and protected gates validate that design.

This work must preserve exact repository/ref/tree verification, accepted-source lineage, non-force behavior, Preview-only autonomous publication, human REVIEW, and all existing provider/credential/merge/production authority ceilings.

A future browser/behavioral verifier that converts currently unverified static-web acceptance criteria into protected behavioral proof remains a separate governed capability. P2-V0.23.41 does not introduce one.

## Authoritative-record reconciliation

- `CURRENT-STATE.md`: updated because P2-V0.23.41 is merged, deployment-verified, production-accepted on the frozen W9-S1 correction cycle, and the independent source-republication condition is now explicitly tracked as P2-V0.23.42.
- `ARCHITECTURE.md`: remains authoritative at v3.50; the durable REVIEW-rework semantics were already recorded by the P2-V0.23.41 release and this reconciliation adds no architecture change.
- `DESIGN-SYSTEM.md`: unchanged; no durable visual-system rule changed during production acceptance.
- `PROJECT-CONSTITUTION.md`: unchanged; least privilege, explicit human control, fail-closed evidence, and human REVIEW authority remain intact.
