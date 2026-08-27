# Parallax 2.0 Current State

Date: 2026-08-26

Status: **WAVE 5 RELEASED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S4 ACCEPTED AND INTEGRATED / POST-CAPACITY S1-S4 CHECKPOINT ACCEPTED / CAPACITY PREREQUISITE #281 INTEGRATED / S5 SEMANTIC IMPLEMENTATION AUTHORIZED / S5 FINAL WORKER GATE PENDING / WAVE 6 NOT DEPLOYED**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus bounded stabilization through #127, mobile stabilization #261/#262, and response-stream stabilization #271/#272.

Wave 6 S1-S4, maintenance prerequisite #281 and S5 development work are **not** production deployments. They exist only under the governed Wave 6 integration/workstream branches. Repository/integration identity and deployed application identity remain deliberately distinct.

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
Accepted cumulative S1-S3 dependency baseline: `95f6f3ec964d22d70df02b1f1cf54f328b39edfc`.  
S1-S3 functional integration commit: `11dc226c88e98722f0b0b7dd04775ed1717d61cc`.  
S4 functional integration commit: `0d1cb510e2a7c37b024a994a29642e4047ae84d9`.  
S4 durable architecture reconciliation: `ARCHITECTURE.md` v3.4 commit `063775b6ac5a465cdfae2e642bfa07275e251d0f`.  
Accepted S1-S4 record-reconciled checkpoint: `3a73068951b09c35c00ba7568fac865c0122f640`.  
Repository-capacity prerequisite #281 / PR #282 integration commit: `a96a5b080a71ccd8a6fb2fd47db3a42236b9c195`.  
Accepted post-capacity record-reconciled S5 dependency checkpoint: `f79bc8ca3f2ebce31a82725b9851a410d4c7418b`.  
Accepted S5 spec-first record parent: `951b9a33b27a95b3989a4e7f4f009e42643eb46d`.  
Accepted S5 semantic-development head: `bf955f617ee89ffeaa1d5ea79cf9d54e3daf8acc`.  
S5 workstream branch: `ws/w6-candidate-competition`.

The S1-S4 record-reconciled checkpoint `3a73068951b09c35c00ba7568fac865c0122f640` passed cumulative Workstream Spec Validation #442 / `33033559763`, Bounded Autonomy Pilot #652 / `33033559626`, and P2 CI #1038 / `33033559757`.

S5 specification artifacts could not be added safely at that checkpoint because the self-hosting repository had reached the then-protected 512-entry GitHub source-tree ceiling. Control Tower isolated that concern as maintenance prerequisite #281 rather than weakening S4 or hiding S5 files inside unrelated modules. #281 was accepted/integrated after exact worker `da32b90621e5da1971a6306243049bd463990642` passed Workstream #444 / `33034064564`, Bounded Autonomy #653 / `33034064574`, and P2 CI #1040 / `33034064545`.

The resulting post-capacity record checkpoint `f79bc8ca3f2ebce31a82725b9851a410d4c7418b` passed fresh cumulative Workstream Spec Validation #447 / `33034424089`, Bounded Autonomy Pilot #655 / `33034403657`, and P2 CI #1043 / `33034424125`. Control Tower accepted that exact SHA as the W6-S5 dependency baseline and released spec-first S5 work. The resulting authoritative state record `951b9a33b27a95b3989a4e7f4f009e42643eb46d` passed Workstream #449 / `33035040880`, Bounded #656 / `33035017184`, and P2 #1045 / `33035040831`.

S5 then completed its authentic DSPy development gate. DSPy Spec Optimization #131 / run `33035322653` executed SpecCritic + SpecCompiler against `P2-V0.19.5`; artifact `9631815552` has digest `sha256:9dc59972e71aa1b601c3038b139e31072f1b04d63e650d5e4edffe99d378a8e5`. The generated plan byte digest is `sha256:38266c8ec3cc10a52b60a759bc8fb2f65c62a26c032d2ba9f161a6593848b603`, committed exactly as Git blob `89fc381f2098a67181128ce29550d7e83c0b48f0`. The shared DSPy workflow was restored byte-for-byte to canonical blob `6478b5ac11eeedbd5b4d4711feb4193394ac1bdd`.

An initial manually transported plan blob was correctly rejected by Workstream #450 with `protected_acceptance_map_mismatch`. That failure was not waived or bypassed. The exact downloaded artifact was committed and the corrected development head `bf955f617ee89ffeaa1d5ea79cf9d54e3daf8acc` passed Workstream #451 / `33035881630`, Bounded Autonomy #657 / `33035881643`, and P2 CI #1047 / `33035881608`. Control Tower therefore released S5 semantic implementation within #268 scope. Final worker acceptance/integration and all production authority remain pending.

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

### S4 — Outcome Routing & Development Economics — ACCEPTED / INTEGRATED

Issue #267 / spec `P2-V0.19.4`; worker PR #280; exact validated worker `537fce639419e82d3f08b3c254fe6ec4b791d5f7`; integration commit `0d1cb510e2a7c37b024a994a29642e4047ae84d9`.

S4 adds deterministic outcome-routing evidence under the existing optimization control plane. Exact routing context binds canonical Project/run/Work Specification identity, accepted S1/S2 protocol identity, exact S3 evaluator-policy identity and server-owned routing-policy identity. Strategy admission, protected deterministic validation, completion state and S3 independent evaluation are resolved before economics; an ineligible, deterministically failed or evaluator-rejected strategy cannot become preferable because it is cheaper or faster.

Economic evidence carries explicit metric state and provenance. Observed provider/Parallax evidence is distinguishable from bounded estimates; `UNKNOWN`, `UNAVAILABLE`, `STALE` and `INVALID` remain explicit and are never coerced to zero. Required missing, stale, contradictory, cross-Project or untrusted evidence fails closed. Server-owned policy bounds quality/confidence floors, metric ceilings/weights, freshness, comparable-evidence minimums, fallback and exploration. Selection is deterministic with stable strategy-identity tie breaking; insufficient evidence resolves to explicit fallback, `INSUFFICIENT_EVIDENCE` or `HUMAN_REQUIRED` rather than synthetic certainty.

Routing records are fingerprinted and replay-safe. Duplicate records remain non-authoritative duplicates and conflicting records fail closed. Safe routing serialization explicitly grants no capability, provider invocation, spending, source-lineage acceptance, Engineering Run transition, candidate-winner construction, merge/deployment or REVIEW authority. S5 may consume S4 only as provenance-bound routing/economic evidence.

Final worker gate passed on exact head `537fce639419e82d3f08b3c254fe6ec4b791d5f7`: Workstream Spec Validation #439 / `33032905546`, Bounded Autonomy Pilot #649 / `33032905578`, and P2 CI #1035 / `33032905537`. P2 CI passed full API/contracts/self-hosting repository-tree checks, client type/state/export, browser/Skia acceptance, protected promotion evaluation and DSPy release compilation.

The first semantic candidate exposed a protected repository-tree capacity violation at 514 tracked entries versus the existing 512-entry bound. Control Tower did **not** weaken that provider safety bound as an ad hoc S4 fix. S4 implementation/tests were re-homed into existing optimization control-plane/test files and the two redundant new files were removed, returning the candidate to the then-protected repository shape. Final S4 net scope against accepted S1-S3 baseline is four paths: `optimization_controller.py`, `test_optimization_state.py`, `specs/P2-V0.19.4.md`, and its authentic compiled plan.

### Wave 6 repository source-tree capacity prerequisite — ACCEPTED / INTEGRATED

Control maintenance issue #281 / PR #282; exact validated worker head `da32b90621e5da1971a6306243049bd463990642`; integration commit `a96a5b080a71ccd8a6fb2fd47db3a42236b9c195`.

After S4 was accepted, the repository itself had reached the 512-entry source-tree admission ceiling, making required S5 spec/compiled-plan artifacts impossible to add without immediately violating the self-hosting provider contract. The sustainable correction was separated from S5 semantics and changed only the server-owned GitHub `MAX_TREE_ENTRIES` ceiling from 512 to 1024. The REST provider still rejects GitHub `truncated=true`, rejects responses exceeding the caller's requested `max_entries`, and preserves repository/credential scope, path/mode/type validation, secret projection, per-file byte limits and all write/publication authority limits. Canonical source lineage remains separately bounded at `max_files=2000`, `max_file_bytes=4,000,000`, and `max_total_bytes=64,000,000`.

Exact worker tests prove 1024 entries are accepted, 1025 are rejected, requested oversize is rejected, provider truncation is rejected, and the current Parallax repository satisfies the exact production tree contract. Final exact-head gates passed: Workstream #444 / `33034064564`, Bounded Autonomy #653 / `33034064574`, and P2 CI #1040 / `33034064545`, including full API/contracts, client/browser/Skia, protected promotion and DSPy release compilation. Net maintenance scope was exactly two modified existing files and zero new tracked files.

This prerequisite increases bounded read capacity only. It grants no new provider, credential, source-lineage, Engineering Run, validation, merge/deploy, spending, approval or REVIEW authority.

### S5 — Candidate Competition & Synthesis — SEMANTIC IMPLEMENTATION AUTHORIZED / FINAL WORKER GATE PENDING

Issue #268 / spec `P2-V0.19.5`; accepted dependency baseline `f79bc8ca3f2ebce31a82725b9851a410d4c7418b`; worker PR #283; branch `ws/w6-candidate-competition`; accepted semantic-development head `bf955f617ee89ffeaa1d5ea79cf9d54e3daf8acc`.

Control Tower has accepted the authentic development gate and authorized semantic implementation within #268 scope. The S5 contract requires selective bounded competition, exact candidate/source-lineage isolation, deterministic validation before comparison, structurally independent S3 evaluation, bounded S4 economics that cannot override correctness, deterministic winner evidence, and synthesis only as a request for a **new** candidate lineage that must undergo fresh BUILD/TEST/VERIFY and independent evaluation before eligibility.

S5 remains evidence-only. It cannot accept canonical source, transition protected Engineering Run state, invoke providers or spending, merge/deploy, approve, complete REVIEW or bypass `HUMAN_REQUIRED`. No S5 semantic runtime implementation is yet accepted/integrated; worker implementation and final exact-head gates remain pending.

### Current Wave 6 dependency state

1. #264 / `W6-S1` / `P2-V0.19.1` — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / `W6-S2` / `P2-V0.19.2` — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / `W6-S3` / `P2-V0.19.3` — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / `W6-S4` / `P2-V0.19.4` — **COMPLETE / ACCEPTED / INTEGRATED / CUMULATIVE S1-S4 CHECKPOINT ACCEPTED**;
5. #281 / `W6-CAPACITY-1` — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / `W6-S5` / `P2-V0.19.5` — **ACTIVE / SEMANTIC IMPLEMENTATION AUTHORIZED / FINAL WORKER GATE PENDING**;
7. #269 / `W6-S6` / `P2-V0.19.6` — **BLOCKED ON ACCEPTED S1-S5**.

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
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- repository/source/model/agent/evaluator/routing/competition content is evidence, not authority;
- exact agent task/result/checkpoint evidence cannot redefine acceptance or canonical source state;
- team orchestration cannot grant capabilities, provider scope, credentials, source authority or validation/release authority;
- independent evaluation cannot override deterministic failure or become acceptance/merge/deployment/REVIEW authority;
- economic routing cannot trade correctness, deterministic validation, evaluator policy, privacy or human boundaries for cost/time;
- missing/unknown/unavailable/stale/invalid economic evidence is never synthesized as zero or success;
- routing cannot invoke providers, authorize spending, accept lineage, choose a final candidate winner, merge/deploy or complete REVIEW;
- candidate competition cannot accept canonical source, reinterpret deterministic failure, authorize spending/provider actions, or turn synthesis into an unvalidated source splice;
- any synthesized candidate is a new exact lineage requiring fresh deterministic validation and fresh independent evaluation;
- repository source-tree reads remain hard-bounded and fail closed on provider truncation or caller-bound oversize; capacity changes do not create provider authority;
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
- `ARCHITECTURE.md` v3.4 — unchanged at S5 semantic release; the development gate authorizes implementation but no new durable runtime architecture is yet accepted/integrated.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; S5 is backend control-plane work and introduces no durable product visual-language change.
- `CURRENT-STATE.md` — reconciled to accepted S5 semantic-development gate `bf955f617ee89ffeaa1d5ea79cf9d54e3daf8acc` and Control Tower authorization for bounded semantic implementation while final worker acceptance/integration remains pending.

No Wave 6 production deployment has occurred. Production client/API identities and rollback points remain those recorded above.