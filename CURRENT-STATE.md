# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION PRODUCTION-VERIFIED / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S5 ACCEPTED AND INTEGRATED / WAVE 6 NOT DEPLOYED / S6 BLOCKED PENDING FRESH CUMULATIVE S1-S5 RECORD CHECKPOINT**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through #127, mobile #261/#262, response-stream #271/#272, and the P2-V0.18.10 model-transport correction tracked by #284 / PR #288.

Wave 6 S1-S5 are accepted development architecture on `integration/wave6-agentic-control-plane`; they are **not** production deployments. Repository/integration identity and deployed application identity remain deliberately distinct.

### Production repository / release identity

- production source branch: `main`;
- exact current application/source merge: `e6fc6900239df436545318e6ab7f532d0d3789bc`;
- governing corrective spec: `P2-V0.18.10`;
- corrective worker branch: `p2/provider-gateway-oidc-stabilization`;
- exact validated worker head: `e654cf9b245aa3ff33f44343cb7d836dd9a8e8a9`;
- PR #288 merged with expected-head protection;
- authentic DSPy SpecCritic + SpecCompiler run: `33088339454` — PASS;
- evidence artifact: `9653273016`;
- artifact digest: `sha256:55fb185c1192f91783fb0cd21426102a85802063b3e4260c7e710a495e053c77`.

Exact worker head `e654cf9b245aa3ff33f44343cb7d836dd9a8e8a9` passed Workstream Spec Validation #460, Bounded Autonomy Pilot #665 and P2 CI #1056, plus exact-head Vercel Preview validation. The resulting `main` merge `e6fc6900239df436545318e6ab7f532d0d3789bc` also passed fresh post-merge API/contracts, client/browser/Skia, protected promotion, changed-spec protected-plan and DSPy release checks.

### Production client

- Vercel project: `parallax`;
- deployment remains `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2`;
- state: `READY`;
- target: `production`;
- exact client Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

P2-V0.18.10 is API-only. Vercel correctly suppressed/cancelled a redundant client build for the API-only source change, so no new client artifact is claimed. The existing deployment-verified client remains authoritative.

### Production API

- Vercel project: `parallax-api`;
- production deployment: `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `e6fc6900239df436545318e6ab7f532d0d3789bc`;
- public production alias: `parallax-api-tan.vercel.app`.

Post-cutover verification on that exact deployment established:

- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- authenticated browser/session traffic reached the exact deployment successfully;
- authenticated `POST /v1/conversations/aa1e2a0b-760e-40e7-8a3a-b79a1abc41d4/work-specifications/draft` → HTTP 200;
- exact request logs recorded sanitized routing identity `parallax_model_transport transport=vercel_ai_gateway model=openai/gpt-5.6-luna`;
- LiteLLM completed the canonical `gpt-5.6-luna` call successfully through the OpenAI-compatible transport;
- exact-deployment runtime-error scan after the authenticated smoke found no runtime errors.

This satisfies the P2-V0.18.10 end-to-end Capture Spec acceptance criterion that P2-V0.18.9 failed.

A non-fatal DSPy disk-cache warning was observed in the serverless runtime because the default cache directory is not writable/creatable there. DSPy fell back to memory-only cache and the authenticated request completed successfully. This is an efficiency/operational observation, not a release correctness failure or authority bypass.

## P2-V0.18.10 model-transport stabilization

The prior P2-V0.18.9 production deployment `dpl_C5sdDZgnwq8uSKFkA7DkJc4rCW82` was infrastructure-ready but failed authenticated Capture Spec with HTTP 429. Runtime evidence showed Luna → Terra → Sol exhaustion while LiteLLM treated the request as direct OpenAI provider traffic. That release therefore was not accepted as functionally verified model routing.

P2-V0.18.10 preserves canonical model identities and escalation order:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

For hosted production model traffic, Parallax now binds the validated request-scoped `x-vercel-oidc-token` to the fixed OpenAI-compatible Vercel AI Gateway endpoint `https://ai-gateway.vercel.sh/v1`. Canonical model IDs remain unchanged. Process-environment `VERCEL_OIDC_TOKEN` is not production model-provider authority. Explicit server-owned `DSPY_API_BASE` / `DSPY_API_KEY` configuration remains the deliberate override path. Production fails closed without admitted request OIDC or that explicit override; there is no silent direct-OpenAI fallback.

The request-scoped credential is propagated only through bounded request context into downstream DSPy construction for conversation scope/reason, Work Specification drafting and protected implementation generation. It is not persisted, logged, shipped to the client, placed in prompts/source packages, or forwarded into sandboxes.

## Deployment-verified stabilization retained

### Mobile #261 / PR #262

The mobile release remains deployment-verified. It provides mobile primary destinations `Chat`, `Build`, and `Project`; conversation-first Chat; full-screen Work Specification review; plain-language `SPEC_AMENDMENT` recovery; guided Build lifecycle; canonical Project/conversation switching; compact authenticated access behavior; and Live Build return-to-chat semantics while preserving server-owned authority.

Historical mobile identities retained:

- exact validated worker: `56f6d2a81112e592b1128df2b96506ae2d923650`;
- application merge: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- known-good mobile client rollback: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`.

### Response-stream #271 / PR #272

The response-stream correction remains deployment-verified. It distinguishes provider-capacity exhaustion from protected scope/reason validation failure, preserves the durably submitted user turn, and does not change model/provider order, credentials, Project/spec/source authority, approval or REVIEW boundaries.

Historical accepted identities retained:

- exact validated worker: `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa`;
- application merge: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- former production API: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`;
- current production client remains the exact client artifact from that release.

## Wave 5 baseline retained

Control Tower #215 completed the generalized application-delivery program through #216-#221 / `P2-V0.18.1`-`P2-V0.18.6`. Final Wave 5 application release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Later production stabilization is cumulative and does not replace its authority model.

## Wave 6 — Agentic Development Control Plane

Control Tower: #263.  
Integration branch: `integration/wave6-agentic-control-plane`.  
Current accepted S1-S5 functional integration head: `9fe751a96ec050545abdcfbb016c668cd4c7336f`.  
Wave 6 production deployment: **none**.

### S1 — Agent Adapter & Evidence Protocol — ACCEPTED / INTEGRATED

- issue #264 / spec `P2-V0.19.1`;
- exact validated worker `8cc911128d41dc648f2fb6136524edb3e35cfeaf`;
- integration commit `78720fbfcce3adba508765e30c5e452f1bd33b9e`.

S1 establishes provider-neutral engineering agents as bounded labor with exact Project/run/spec/acceptance/task/attempt binding, typed evidence, replay/stale-result admission and explicit usage provenance. It creates no second source-lineage, deterministic-validation, provider, release, approval or REVIEW authority path.

### S2 — Dynamic Development Team Orchestration — ACCEPTED / INTEGRATED

- issue #265 / spec `P2-V0.19.2`;
- exact validated worker `fc27331628b8f2a975a7bb63b21255c7784a5de3`;
- integration commit `78d25beffd21bb983fadcd179b3124c325c25a55`.

S2 composes S1 evidence into deterministic bounded team formation, dependency-safe scheduling and durable evidence-driven reassignment. Team formation remains labor orchestration evidence and cannot grant capabilities/credentials/provider access, accept source, decide final quality, merge/deploy or bypass REVIEW/HUMAN_REQUIRED.

### S3 — Independent Evaluation & Quality Judgment — ACCEPTED / INTEGRATED

- issue #266 / spec `P2-V0.19.3`;
- exact validated worker `cd16885d75931223d460468f6b14569b047c99b2`;
- integration commit `11dc226c88e98722f0b0b7dd04775ed1717d61cc`.

S3 provides exact-candidate, independent, provenance-bound quality evidence. Deterministic protected validation is authoritative first; producer self-evaluation cannot satisfy independence; evaluator policy is immutable/server-owned; replay is fingerprinted and fail-closed. `SUPPORTED` is evidence only, not source acceptance, provider/spending, merge/deploy or REVIEW authority.

### S4 — Outcome Routing & Development Economics — ACCEPTED / INTEGRATED

- issue #267 / spec `P2-V0.19.4`;
- exact validated worker `537fce639419e82d3f08b3c254fe6ec4b791d5f7`;
- integration commit `0d1cb510e2a7c37b024a994a29642e4047ae84d9`.

S4 adds deterministic outcome-routing evidence under the existing optimization controller. Eligibility/correctness is resolved before economics; observed, estimated, unavailable, unknown, stale and invalid evidence remain distinct; quality/confidence floors are non-tradeable; decisions are replay-safe and confer no provider/spending/source/run/release authority.

### Repository source-tree capacity prerequisite #281 / PR #282 — ACCEPTED / INTEGRATED

- exact validated worker `da32b90621e5da1971a6306243049bd463990642`;
- integration commit `a96a5b080a71ccd8a6fb2fd47db3a42236b9c195`.

The bounded GitHub source-tree ceiling was increased from 512 to 1024 after S4 exposed that the self-hosting repository had reached the former ceiling. Provider truncation, caller-request bounds, repository/credential scope, path/type validation, secret projection, byte limits and write/publication authority remain fail-closed. This is bounded read capacity only.

### S5 — Candidate Competition & Synthesis — ACCEPTED / INTEGRATED

- issue #268 / spec `P2-V0.19.5`;
- accepted dependency baseline `f79bc8ca3f2ebce31a82725b9851a410d4c7418b`;
- authoritative semantic parent `192ec4e369f26df56eb1750b8a831a77ae9aabd2`;
- exact final validated worker `4233219245b63084e1160967b3c77e212cf6178e`;
- integration merge `9fe751a96ec050545abdcfbb016c668cd4c7336f`;
- authentic DSPy run `33035322653`, artifact `9631815552`, digest `sha256:9dc59972e71aa1b601c3038b139e31072f1b04d63e650d5e4edffe99d378a8e5`;
- final worker gates: Workstream #456 / `33038223093`, Bounded Autonomy #661 / `33038223110`, P2 CI #1052 / `33038223102` — PASS.

S5 selectively competes already-admissible candidates only when bounded server-owned policy and accepted S2/S3/S4 evidence justify the extra work. Candidates remain exact-lineage isolated; deterministic failure disqualifies regardless of quality/economic score; evaluator evidence must remain independent; deterministic replay-safe winner evidence does not itself accept source.

Synthesis creates a distinct new candidate lineage rather than splicing unvalidated fragments. The synthesized candidate requires fresh exact-lineage BUILD/TEST/VERIFY, deterministic validation and fresh independent evaluation before eligibility. Competition/synthesis cannot invoke provider spending, accept canonical source, mutate protected Engineering Run state, merge/deploy, approve, complete REVIEW or bypass HUMAN_REQUIRED.

### Current Wave 6 dependency state

1. #264 / S1 — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / S2 — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / S3 — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / S4 — **COMPLETE / ACCEPTED / INTEGRATED**;
5. #281 capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / S5 — **COMPLETE / ACCEPTED / INTEGRATED**;
7. #269 / S6 — **BLOCKED pending authoritative S5 record reconciliation on the integration branch plus a fresh cumulative exact-head S1-S5 gate**.

PR #275 remains the long-lived DRAFT / DO NOT MERGE integration-validation surface. No Wave 6 production promotion has occurred.

## Rollback

Rollback is component-specific and governed; Wave 6 integration is not part of production rollback because Wave 6 is not deployed.

### API rollback

The immediately preceding P2-V0.18.9 deployment `dpl_C5sdDZgnwq8uSKFkA7DkJc4rCW82` is **not** a functionally accepted model-routing rollback because authenticated Capture Spec failed there. If rollback of P2-V0.18.10 is required, Control Tower must select a prior deployment deliberately based on the failure being mitigated rather than treating P2-V0.18.9 as known-good.

The earlier response-stream-stabilized API `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y` at `9767b2520d74c70bd1a2ec2e951480da223b45f7` remains a historical exact deployment reference, but it predates the Gateway correction and is not represented as solving current hosted-model capacity/transport behavior.

### Client rollback

- prior known-good mobile deployment: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`;
- exact client Git SHA: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32 and Wave 6 Control Tower #263 remain active durable program records;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- worker branches start only from exact accepted dependency/baseline state and target governed integration where required;
- workers stop `READY FOR INTEGRATION` and do not merge/deploy by default;
- Control Tower serializes accepted composition, cumulative validation, authoritative-record maintenance and production promotion;
- source-integrated Wave 6 work is not production merely because it exists on an integration branch;
- standing single-user production-promotion authority never waives exact-head gates, rollback, least privilege, post-cutover evidence or the Preview/REVIEW boundaries;
- no production claim is valid without exact release identity plus post-cutover verification.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- repository/source/model/agent/evaluator/routing/competition content is evidence, not authority;
- team orchestration cannot grant capabilities, provider scope, credentials, source authority or validation/release authority;
- independent evaluation cannot override deterministic failure or become acceptance/merge/deployment/REVIEW authority;
- economic routing cannot trade correctness, deterministic validation, evaluator policy, privacy or human boundaries for cost/time;
- missing/unknown/unavailable/stale/invalid economic evidence is never synthesized as zero or success;
- candidate competition cannot accept canonical source, reinterpret deterministic failure, authorize spending/provider actions or turn synthesis into an unvalidated source splice;
- any synthesized candidate is a new exact lineage requiring fresh deterministic validation and independent evaluation;
- repository source-tree reads remain hard-bounded and fail closed on provider truncation/caller oversize;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- correction cannot weaken acceptance/evaluation policy;
- skills, service bindings, repository intelligence, engineering memory, agents and adapters cannot create execution/provider/deployment/approval authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- production hosted-model identity and transport are server-owned; request OIDC cannot broaden tool/provider/deployment authority and there is no silent direct-provider fallback;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.5 — updated because S5 is now accepted/integrated as durable Wave 6 architecture and P2-V0.18.10 established a durable production hosted-model transport/credential-admission contract.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; neither S5 nor the model-transport correction changes durable product visual language or interaction semantics.
- `CURRENT-STATE.md` — updated for the exact P2-V0.18.10 production release and end-to-end verification, current component deployment identities, accepted/integrated S5 state, and the resulting S6 dependency gate.

Wave 6 remains not deployed. The next Wave 6 control action is to reconcile this authoritative S5/production record state onto `integration/wave6-agentic-control-plane`, run a fresh cumulative exact-head S1-S5 gate, and only then decide whether S6 may begin spec-first work.
