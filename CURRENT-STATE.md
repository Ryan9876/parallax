# Parallax 2.0 Current State

Date: 2026-09-02
Status: **P2-V0.23.40 PRODUCTION-ACCEPTED / W9-S1 SOURCE DELIVERY PROVEN / HUMAN REVIEW REQUIRED**
Architecture: `ARCHITECTURE.md` v3.49

## Purpose of this record

This file is the authoritative snapshot of Parallax's current validated state. It intentionally records current production truth, active authority boundaries, the latest accepted release, and material remaining work rather than duplicating the full release history. Historical evidence remains preserved in Git history, versioned specifications, compiled plans, pull requests, workflow runs, and deployment records.

## Current production truth

### API

Current deployment-verified production API application source:

- source: `c31c3c8618a46db99d1403c5340306096cf35727`;
- release: `P2-V0.23.40`;
- production deployment: `dpl_7LzhAbBUUBHKDprMTUTdrgwGU6nk`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- deployment state: `READY`;
- `/health`: HTTP 200 / `ok`;
- `/ready`: HTTP 200 / `ready`, database `ok`, providers `ok`;
- post-acceptance runtime-error scan: clean;
- post-acceptance warning/error/fatal exact-deployment log scan: clean.

The P2-V0.23.40 production build passed the normal provider, exact delivery-permission, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot, static-web candidate-validation, and Engineering Run event-schema preflights before becoming READY.

### Client

Current production client remains the latest READY path-relevant client release; later P2-V0.23.26 through P2-V0.23.40 changes are API/spec/governance-only and their client deployments were path-aware canceled/ignored.

- source: `3d53599c4659162cfe45bbc4809f3f329d0abb73`;
- production deployment: `dpl_HA9KJ1kqy9xUKdQsi8of2zGDiEP4`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`;
- deployment state: `READY`;
- production shell: HTTP 200.

### Execution substrates and authority

Parallax retains deployment-verified source-only engineering paths for the governed Python and .NET validation profiles and the explicit marker-free `static-web-v1` execution contract. The common Python/Node execution snapshot and the dedicated .NET execution snapshot remain server-owned, source-free, deny-all-network validation substrates. Candidate source cannot select commands, snapshots, provider credentials, source lineage, Git publication, Preview authority, lifecycle transitions, merge, or production promotion.

Human `REVIEW` remains the completion boundary. No P2-V0.23.40 change authorizes automatic REVIEW completion, merge, or production promotion of generated applications.

## P2-V0.23.40 — truthful static-web acceptance evidence — PRODUCTION-ACCEPTED

Workstream: #565  
Release PR: #566  
Parent: #391 / W9-S1  
Governing specification: `specs/P2-V0.23.40.md`  
Architecture: v3.49

### Problem closed

The first real W9-S1 Decision Ledger build exposed a systemic evidence defect. The protected `static-web-v1` validator proves bounded structural properties such as source/root safety, required HTML shape, JavaScript syntax, and local references. Before P2-V0.23.40, successful structural TEST/VERIFY execution could be projected as though every Work Specification acceptance criterion had been behaviorally verified.

P2-V0.23.40 separates those concepts. For an exact durable PLAN bound to `static-web-v1` / `GREENFIELD_STATIC_WEB`:

- structural TEST and VERIFY may still pass when their actual server-owned checks pass;
- `acceptance_verification_scope` is persisted as `STRUCTURAL_ONLY`;
- the exact protected acceptance map is persisted as targeted;
- `acceptance_ids_verified` is empty;
- the full targeted acceptance map is explicitly persisted as unverified;
- runtime evaluation independently authenticates the persisted PLAN execution contract and exact verification partition before consuming that evidence;
- structural command success remains valid same-lineage execution evidence but is not behavioral acceptance proof;
- the Engineering Run may reach REVIEW, but structural evidence alone cannot complete REVIEW.

Python and .NET full-verification semantics, execution-contract/profile digests, commands, provider/model/network authority, source-lineage authority, Git/Preview authority, lifecycle authority, and human REVIEW completion authority are unchanged.

### Release evidence

- protected DSPy SpecCritic/SpecCompiler gate `33651595933`: SUCCESS with the exact compiled plan persisted;
- serialized bounded implementation validation `33663382152`: SUCCESS, including strict DSPy-plan validation, API compileall, focused P2-V0.23.40 regressions, full API regression, and patch hygiene;
- exact validated semantic head: `4f1c1a0956c4d01fb5363c79faa44140d8a60976`;
- exact reconciled PR head: `03c5d954a1d27d9ebf3b93bf46541638aebcf03f`;
- PR #566 Bounded Autonomy Pilot `33663958142`: SUCCESS;
- PR #566 Workstream Spec Validation `33663958018`: SUCCESS;
- PR #566 Parallax P2 CI `33663958066`: SUCCESS;
- merge / exact production application source: `c31c3c8618a46db99d1403c5340306096cf35727`;
- post-merge Parallax P2 CI `33664147879`: SUCCESS;
- post-merge Workstream Spec Validation `33664147772`: SUCCESS;
- exact production deployment `dpl_7LzhAbBUUBHKDprMTUTdrgwGU6nk`: READY.

### Production acceptance proof

Dedicated QA production replay `33665556698`, job `100366296330`, completed successfully against Engineering Run `4771a9eb-a939-406e-a0bd-01852a72b63b`.

The persisted PLAN bound:

- `execution_contract_id=static-web-v1`;
- `execution_contract_binding_reason=GREENFIELD_STATIC_WEB`;
- exact acceptance criteria `AC-01` through `AC-05`.

The same bounded run then completed IMPLEMENT, BUILD, TEST, and VERIFY and stopped at `REVIEW` revision `6` with `last_failure_code=null`.

Persisted TEST evidence proved:

- stage status `PASSED`;
- `acceptance_verification_scope=STRUCTURAL_ONLY`;
- `acceptance_ids_verified=[]`;
- targeted IDs = `AC-01` through `AC-05`;
- unverified IDs = `AC-01` through `AC-05`;
- deterministic structural result `STATIC_WEB_TEST_OK`.

Persisted VERIFY evidence proved the same exact scope and partition with deterministic structural result `STATIC_WEB_VERIFY_OK`.

The accepted workflow explicitly reported:

- `TEST: STRUCTURAL_ONLY verified=0 targeted=5 unverified=5`;
- `VERIFY: STRUCTURAL_ONLY verified=0 targeted=5 unverified=5`.

This is the required end-to-end production proof that static-web structural success no longer manufactures behavioral acceptance evidence.

### Acceptance-harness boundaries and cleanup

The first fresh replay attempt encountered `SOURCE_NOT_FOUND` because the isolated QA repository's default branch was intentionally empty. After a temporary minimal static baseline was added solely to exercise the existing non-greenfield static-web path, the same run progressed through PLAN, IMPLEMENT, BUILD, and TEST. VERIFY then encountered a separate source-delivery `BRANCH_NOT_FOUND` while the bounded QA branch was materializing. Neither condition resulted in a Parallax production-code change.

After the delivery branch existed, the same bounded run completed VERIFY and reached REVIEW. Cleanup then restored the QA environment:

- `Ryan9876/parallax-qa/.github/workflows/production-replay.yml` restored byte-for-byte to standing blob `e1a619d44ed26075c0c97eb6cf0b5fa931c2c75f`;
- temporary `Ryan9876/parallax-qa1/main/index.html` removed;
- `parallax-qa1/main` re-verified empty;
- final exact-deployment runtime scans found no runtime errors and no warning/error/fatal logs after the accepted replay.

## W9-S1 — current position

P2-V0.23.39 remains the accepted canonical empty-tree replay/source-delivery foundation. Frozen W9-S1 Engineering Run `a64d56b7-ad42-42ad-9562-891783363f4a` reached REVIEW revision 6 and successfully completed bounded source delivery:

- source lineage: `src:da5d0fb62d34a3228bb56e7a7d82971c8023a536d11944ba71bcaa51a407b871`;
- delivery evidence: `delivery:dpl_7UNQzRjqb7HNraswzxtSxEjyFozP`;
- branch: `parallax/0e20392b-a64d56b7`;
- source commit: `ee945138e84972d6b635b9e9a086e625ef19fccb`;
- GitHub PR #1 in `Ryan9876/parallax-qa1`;
- Vercel Preview `dpl_7UNQzRjqb7HNraswzxtSxEjyFozP`: `READY`;
- run state remains `REVIEW`, preserving human completion authority.

P2-V0.23.40 does not claim that the generated Decision Ledger application behavior is fully accepted. It corrects the evidence contract so any behavioral criteria not actually proven remain explicit at REVIEW rather than being mislabeled as verified.

## Established platform state

- Waves 1–8 remain deployment-verified, including accepted Python and .NET source-only full-experience paths.
- Public commit-bearing GitHub source bootstrap remains independent from application delivery and uses immutable source identity.
- Empty-greenfield repository handling uses the governed exact-repository two-commit baseline and canonical Git empty-tree semantics established through P2-V0.23.37–P2-V0.23.39.
- Hosted implementation routing remains server-owned and bounded `Luna -> Terra -> Sol` with the existing finite recovery rules and no hidden provider retry expansion.
- Safe source mutation, canonical patch/content handling, immutable source-lineage acceptance, disposable BUILD/TEST/VERIFY, provider delivery, and human REVIEW boundaries remain authoritative.
- Dedicated production-QA trust remains bound to the exact `Ryan9876/parallax-qa` repository/workflow identity; temporary QA identities are not standing production authority.

## Remaining governed work

- Human REVIEW remains required for W9-S1 generated-application completion; Parallax has not autonomously approved, merged, or promoted that generated application.
- Any future browser/behavioral verifier that converts currently unverified static-web acceptance criteria into protected proof requires a separately governed capability/specification. P2-V0.23.40 intentionally does not add one.
- Workstream #565 may close as completed after this production-acceptance record reconciliation is merged.

## Authoritative-record reconciliation

- `CURRENT-STATE.md`: updated because P2-V0.23.40 is now merged, deployed, production-accepted, QA-cleaned, and post-acceptance telemetry-verified. This file is also contracted back to a current snapshot so obsolete historical "current" claims cannot outrank newer production evidence.
- `ARCHITECTURE.md`: remains authoritative at v3.49. The durable structural-vs-behavioral verification semantics were already recorded before deployment and production acceptance introduced no further architecture change.
- `DESIGN-SYSTEM.md`: unchanged; P2-V0.23.40 changes no durable visual or interaction-system rule.
- `PROJECT-CONSTITUTION.md`: unchanged; the release preserves existing least-privilege, explicit-authority, fail-closed validation, evidence-truthfulness, and human-REVIEW principles rather than creating a new constitutional rule.

Historical release details remain available through this file's Git history and the corresponding versioned `specs/P2-V0.*.md` records rather than being repeated as potentially stale current-state assertions.
