# Parallax 2.0 Current State

Date: 2026-08-26

Status: **WAVE 5 RELEASED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S3 ACCEPTED AND INTEGRATED / S1-S3 RECORDS RECONCILED / CUMULATIVE EXACT-HEAD VALIDATION PENDING / WAVE 6 NOT DEPLOYED**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus bounded stabilization through #127, mobile stabilization #261/#262, and response-stream stabilization #271/#272.

Wave 6 S1-S3 are **not** production deployments. They are accepted only on the governed Wave 6 integration branch. Repository/integration identity and deployed application identity remain deliberately distinct.

### Production client

- Vercel project: `parallax`;
- deployment: `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2`;
- state: `READY`;
- target: `production`;
- exact application Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- public production alias: `parallax-ashy-one-20.vercel.app`;
- last recorded post-cutover verification: HTTP 200 with clean exact-deployment error/fatal scan.

### Production API

- Vercel project: `parallax-api`;
- deployment: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`;
- state: `READY`;
- target: `production`;
- exact application/API Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- public production alias: `parallax-api-tan.vercel.app`;
- last recorded post-cutover verification: `/health` HTTP 200, `/ready` HTTP 200, database/providers healthy, one provider target, clean exact-deployment error/fatal scan.

### Production repository record

- current `main` / authoritative production-record baseline before Wave 6 integration: `c87d5ec6b2c59a983d1b97f1d4f61d2e02808e5c`;
- this is the record reconciliation after deployment-verified response-stream stabilization #271/#272;
- no Wave 6 source has been promoted to production or recorded as deployment-verified.

## Deployment-verified stabilization retained

### Mobile #261 / PR #262

The mobile release replaced the confusing compact desktop composition with a mobile-specific guided model while preserving server-owned engineering authority. Deployment-verified behavior includes mobile primary destinations `Chat`, `Build`, and `Project`; conversation-first Chat; full-screen Work Specification review; plain-language `SPEC_AMENDMENT` recovery; guided Build lifecycle; canonical Project/conversation switching; compact authenticated access-launcher behavior; and Live Build return behavior that returns to Chat.

Historical mobile release identity:

- exact worker candidate `56f6d2a81112e592b1128df2b96506ae2d923650`;
- application merge `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- prior mobile production deployment `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` remains a known-good client rollback point.

### Response-stream #271 / PR #272

The accepted correction distinguishes provider-capacity exhaustion from genuine protected scope/reason validation failure while preserving the durably submitted user turn and all existing authority boundaries.

Release evidence retained:

- exact validated worker head `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa`;
- PR #272 application merge `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- exact worker gates: Workstream Spec Validation #415, Bounded Autonomy #632, P2 CI #1009 — success;
- exact merge gates: Workstream Spec Validation #417, P2 CI #1011 — success;
- production API/client deployment identities listed above;
- production health/readiness and runtime-error verification passed;
- CURRENT-STATE reconciliation #273 merged as repository record `c87d5ec6b2c59a983d1b97f1d4f61d2e02808e5c` with fresh main P2 CI #1014 passing.

## Wave 5 baseline retained

Control Tower #215 completed the generalized application-delivery program through #216-#221 / `P2-V0.18.1`-`P2-V0.18.6`. Final Wave 5 application release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Production stabilization after that release is cumulative rather than a replacement architecture.

## Wave 6 — Agentic Development Control Plane

Control Tower: #263.  
Integration branch: `integration/wave6-agentic-control-plane`.  
Accepted post-response-stabilization starting baseline: `c87d5ec6b2c59a983d1b97f1d4f61d2e02808e5c`.  
Accepted cumulative S1 checkpoint: `53952ab5010275410f06f5940ffaa89e139016eb`.  
S1-S3 functional integration commit: `11dc226c88e98722f0b0b7dd04775ed1717d61cc`.  
Durable record reconciliation: `CURRENT-STATE.md` S2/S3 reconciliation commit `68a4be6d0de35cd69c3578694c7c1ec9101ee213`; `ARCHITECTURE.md` v3.3 reconciliation commit `8e4687c3469ddb202356712b4aba650be8aa05e6`.

The exact cumulative S1-S3 dependency baseline for S4 is not accepted until fresh cumulative Workstream Spec Validation, Bounded Autonomy and P2 CI pass on the final record-reconciled integration head containing this state update.

### S1 — Agent Adapter & Evidence Protocol — ACCEPTED / INTEGRATED

Issue #264 / spec `P2-V0.19.1`; worker PR #274; exact validated worker `8cc911128d41dc648f2fb6136524edb3e35cfeaf`; integration commit `78720fbfcce3adba508765e30c5e452f1bd33b9e`.

S1 establishes provider-neutral engineering agents as bounded labor with exact Project/run/spec/acceptance/task/attempt binding; typed agent/adapter identity and capability declarations as evidence only; bounded result/checkpoint/evidence references; deterministic stale/revoked/duplicate/replay/competing-terminal admission; explicit usage provenance; privacy-safe serialization; and reference-adapter interchangeability/recovery semantics. It creates no second source-lineage, validation, provider, release, approval or REVIEW authority path.

Exact worker gates passed: Workstream #420 / `33025692576`, Bounded Autonomy #636 / `33025692605`, P2 CI #1016 / `33025692492`; focused protocol suite 34 passed; protected promotion, client/browser/Skia and DSPy release compilation passed.

### S2 — Dynamic Development Team Orchestration — ACCEPTED / INTEGRATED

Issue #265 / spec `P2-V0.19.2`; worker PR #278; exact validated worker `fc27331628b8f2a975a7bb63b21255c7784a5de3`; integration commit `78d25beffd21bb983fadcd179b3124c325c25a55`.

S2 composes S1 agent evidence into deterministic bounded team formation and orchestration. It admits agents only through server-owned eligibility policy; chooses the smallest adequate one-agent or bounded multi-agent team; validates dependency-safe scheduling; conservatively serializes overlapping coordination domains; creates deterministic replay-safe assignment identities; composes S1 task/result admission without acquiring source/run authority; permits reassignment only from durable worker evidence with explicit generation increments; and enforces bounded team, concurrency, retry, replan, reassignment and no-progress limits.

S2 remains labor orchestration evidence. It cannot grant capabilities/credentials/provider access, mutate or accept canonical source, weaken deterministic validation, decide final quality, merge/deploy, approve or bypass REVIEW/HUMAN_REQUIRED.

Exact worker gates passed: Workstream #424 / `33028479989`, Bounded Autonomy #638 / `33028479972`, P2 CI #1020 / `33028480106`; full API regression `673 passed, 1 skipped`; client/browser/Skia, protected promotion and DSPy release compilation passed.

### S3 — Independent Evaluation & Quality Judgment — ACCEPTED / INTEGRATED

Issue #266 / spec `P2-V0.19.3`; worker PR #279; exact validated worker `cd16885d75931223d460468f6b14569b047c99b2`; integration commit `11dc226c88e98722f0b0b7dd04775ed1717d61cc`.

S3 establishes a bounded independent-evaluation evidence layer. Every evaluation binds exact Project/run/Work Specification revision/digest/acceptance IDs, exact candidate/source-lineage identity, producer identity, evaluator identity and server-owned evaluator-policy identity. Protected deterministic validation is authoritative and first; failed/missing/mismatched protected evidence cannot be outvoted by an evaluator. Producer self-assessment cannot satisfy independence. Qualitative findings are bounded, evidence-referenced and privacy-safe with explicit `SUPPORTED`, `DETERMINISTIC_BLOCKED`, `NOT_INDEPENDENT`, `INSUFFICIENT_EVIDENCE`, `POLICY_REJECTED` and `HUMAN_REQUIRED` outcomes. Replay is fingerprinted and duplicate-safe; competing records fail closed.

S3 output is evidence only. It cannot accept lineage, transition protected Engineering Run state, choose provider/spending, choose a candidate winner, merge/deploy, complete REVIEW, grant capabilities or bypass HUMAN_REQUIRED.

Spec/DSPy gate: run `33028365447`, artifact `9629322869`, digest `sha256:46d40930a053654bb0f99bd693bc82cdedfe52307a9e7651728fa38e99c3faea`, protected score `1.000`; reconciled development-gate head `50574a532abad2a67da32205e2524949b3c2f874` passed Workstream #430.

Final exact worker head passed Workstream #431 / `33029830303`, Bounded Autonomy #644 / `33029830299`, and P2 CI #1027 / `33029830337`, including full API/contracts, client/browser/Skia, protected promotion evaluation and DSPy release compilation. Final scope was 0 commits behind accepted S2 and exactly four S3-owned paths.

### Current Wave 6 dependency state

1. #264 / `W6-S1` / `P2-V0.19.1` — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / `W6-S2` / `P2-V0.19.2` — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / `W6-S3` / `P2-V0.19.3` — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / `W6-S4` / `P2-V0.19.4` — **FUNCTIONAL DEPENDENCIES AND RECORD RECONCILIATION SATISFIED; WAITING ONLY FOR FRESH EXACT-HEAD CUMULATIVE VALIDATION BEFORE SPEC-FIRST WORKER START**;
5. #268 / `W6-S5` / `P2-V0.19.5` — **BLOCKED ON ACCEPTED S4 OUTCOME EVIDENCE**;
6. #269 / `W6-S6` / `P2-V0.19.6` — **BLOCKED ON ACCEPTED S1-S5**.

PR #275 remains the do-not-merge integration validation surface. No Wave 6 production promotion has occurred.

## Rollback

Current production rollback remains independent of Wave 6 integration because Wave 6 has not been deployed.

### API rollback

- prior deployment `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q`;
- state `READY`;
- exact API Git SHA `5ec7eabc046b9995c8d11d5081df15b986a558fe`.

### Client rollback

- prior mobile deployment `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`;
- state `READY`;
- exact client Git SHA `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

The earlier stabilization-through-#127 client deployment `dpl_642fFKXWzZfA7pkezAYrJbuANXZn` / `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5` and the prior full API/client pair from #245 remain broader historical rollback references.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32 and Wave 6 Control Tower #263 remain active durable program records;
- every semantic AI/runtime workstream is spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- worker branches start only from the exact accepted dependency/baseline state and target the governed integration branch;
- worker chats stop `READY FOR INTEGRATION` and do not merge/deploy by default;
- Integration / Control Tower serializes accepted composition, cumulative validation, authoritative-record maintenance and production promotion;
- source-integrated Wave 6 work is not production merely because it exists on the integration branch;
- standing single-user production-promotion authority does not waive gates, rollback, least privilege, post-cutover evidence, or the Preview/REVIEW boundaries for Parallax-developed Projects;
- no production claim is valid without exact release identity and post-cutover verification.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks model, agent or evaluator judgment;
- repository/source/model/agent/evaluator content is evidence, not authority;
- exact agent task/result/checkpoint evidence cannot redefine acceptance or canonical source state;
- team orchestration cannot grant capabilities, provider scope, credentials, source authority or validation/release authority;
- independent evaluation cannot override deterministic failure or become acceptance/merge/deployment/REVIEW authority;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- correction cannot weaken acceptance/evaluation policy;
- skills, service bindings, repository intelligence, engineering memory, agents and adapters cannot create execution/provider/deployment/approval authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery semantics remain authoritative;
- no silent repository switching, credential refresh, session extension, approval, merge or deployment authority is introduced by Wave 6;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.3 — reconciled because accepted S2 and S3 establish durable bounded team-orchestration and independent-evaluation contracts while preserving all pre-existing authority boundaries.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; S2/S3 introduce no durable product visual-language change.
- `CURRENT-STATE.md` — reconciled to accepted/integrated S1-S3 and the final cumulative exact-head validation gate for S4.

No Wave 6 production deployment has occurred. Production client/API identities and rollback points remain those recorded above.