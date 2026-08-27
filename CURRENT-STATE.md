# Parallax 2.0 Current State

Date: 2026-08-26

Status: **WAVE 5 RELEASED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1 ACCEPTED AND INTEGRATED / S2-S3 DEPENDENCY GATE RELEASED / WAVE 6 NOT DEPLOYED**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus bounded stabilization through #127, mobile stabilization #261/#262, and response-stream stabilization #271/#272.

Wave 6 S1 is **not** a production deployment. It is accepted only on the governed Wave 6 integration branch. Repository/integration identity and deployed application identity remain deliberately distinct.

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

The mobile release replaced the confusing compact desktop composition with a mobile-specific guided model while preserving server-owned engineering authority. Deployment-verified behavior includes:

- mobile primary destinations `Chat`, `Build`, and `Project`;
- conversation-first Chat with a persistent touch-safe composer;
- full-screen Work Specification review;
- plain-language `SPEC_AMENDMENT` recovery;
- guided Build lifecycle with authoritative engineering evidence;
- canonical Project/conversation switching;
- compact authenticated access-launcher behavior;
- Live Build return behavior that returns to Chat;
- no API/runtime, credential, source-lineage, provider, approval, REVIEW/HUMAN_REQUIRED, merge, or deployment authority broadening.

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

Control Tower #215 completed the generalized application-delivery program:

1. #216 / `P2-V0.18.1` — Repository Intelligence & Compatibility;
2. #217 / `P2-V0.18.2` — Governed Skills Runtime;
3. #218 / `P2-V0.18.3` — Application Service Bindings;
4. #219 / `P2-V0.18.4` — Objective-to-Application Orchestration;
5. #220 / `P2-V0.18.5` — Validated Engineering Memory & Reuse;
6. #221 / `P2-V0.18.6` — Generalization Benchmark & Integrated Reference Proof.

Final Wave 5 application release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Production stabilization after that release is cumulative rather than a replacement architecture.

## Wave 6 — Agentic Development Control Plane

Control Tower: #263.

Integration branch: `integration/wave6-agentic-control-plane`.

Accepted post-response-stabilization starting baseline: `c87d5ec6b2c59a983d1b97f1d4f61d2e02808e5c`.

### S1 — Agent Adapter & Evidence Protocol — ACCEPTED / INTEGRATED

Issue: #264  
Spec: `P2-V0.19.1`  
Worker branch: `ws/w6-agent-adapter-protocol`  
Worker PR: #274  
Exact validated worker head: `8cc911128d41dc648f2fb6136524edb3e35cfeaf`  
Exact S1 integration commit: `78720fbfcce3adba508765e30c5e452f1bd33b9e`

S1 establishes a provider-neutral protocol for engineering agents as bounded labor. The accepted contract provides:

- exact canonical Project/run/Work Specification revision/digest/acceptance binding;
- exact operation/request/attempt and optional source-lineage context binding;
- typed agent and adapter identity/version/capability declarations as evidence only;
- bounded result/checkpoint/evidence references;
- normalized lifecycle, recoverable failure, terminal failure, timeout and cancellation evidence;
- deterministic stale/revoked/duplicate/replay/competing-terminal admission behavior;
- explicit observed/unavailable/unknown usage semantics with provenance;
- privacy-safe evidence that excludes raw provider payloads, credentials, secret handles, arbitrary URLs, prompts and hidden reasoning;
- at least two deterministic reference adapter behaviors demonstrating interchangeability/recovery semantics without transferring authority.

S1 does **not** create a second Engineering Run, worker, source-lineage, validation or release authority path. Agent/adapter output cannot accept canonical lineage, change acceptance criteria, grant tools/capabilities/credentials, obtain unrestricted shell/network access, merge/deploy, approve, or bypass REVIEW/HUMAN_REQUIRED.

### S1 spec-first and exact-head evidence

Refreshed DSPy development gate:

- run `33023537013` — success;
- artifact `9627539434`;
- artifact digest `sha256:ae89ef99a16d6afc14a71f7174c954e328d469986ca8d0c1eff7a0783e7f2494`;
- protected score `1.000`;
- authentic compiled plan `specs/compiled/P2-V0.19.1.plan.json` committed;
- `validate_spec.py ... --require-dspy` passed;
- temporary branch-local DSPy workflow trigger restored before final implementation candidate.

Exact worker head `8cc911128d41dc648f2fb6136524edb3e35cfeaf` passed:

- Workstream Spec Validation #420 / run `33025692576`;
- Bounded Autonomy Pilot #636 / run `33025692605`;
- P2 CI #1016 / run `33025692492`;
- full API regression;
- focused S1 protocol suite — 34 passed;
- client/browser/Skia acceptance;
- protected promotion evaluation;
- DSPy release compilation.

PR #274 was merged with expected-head protection into the Wave 6 integration branch. No production promotion occurred.

### Current Wave 6 dependency state

1. #264 / `W6-S1` / `P2-V0.19.1` — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / `W6-S2` / `P2-V0.19.2` — **AUTHORIZED TO BEGIN SPEC-FIRST FROM ACCEPTED S1 DEPENDENCY STATE**;
3. #266 / `W6-S3` / `P2-V0.19.3` — **AUTHORIZED TO BEGIN SPEC-FIRST FROM ACCEPTED S1 DEPENDENCY STATE**;
4. #267 / `W6-S4` / `P2-V0.19.4` — telemetry/contracts may be designed, but final routing remains dependent on trustworthy accepted S1-S3 evidence;
5. #268 / `W6-S5` / `P2-V0.19.5` — dependency-blocked on S2/S3/S4;
6. #269 / `W6-S6` / `P2-V0.19.6` — dependency-blocked on accepted S1-S5.

S2 and S3 must each begin from exact accepted dependency baseline `78720fbfcce3adba508765e30c5e452f1bd33b9e` or a later Control-Tower-recorded integration head. Their semantic implementation remains blocked until each has its own valid Work Specification with stable acceptance IDs and authentic committed DSPy SpecCritic + SpecCompiler evidence.

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
- deterministic/protected validation outranks model or agent judgment;
- repository/source/model/agent content is evidence, not authority;
- exact agent task/result/checkpoint evidence cannot redefine acceptance or canonical source state;
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
- `ARCHITECTURE.md` v3.2 — updated because accepted S1 establishes a durable provider-neutral engineering-agent task/evidence/admission contract while preserving all pre-existing authority boundaries.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; S1 has no durable product visual-language change.
- `CURRENT-STATE.md` — updated because S1 passed its exact-head gates, was accepted and integrated, #264 completed, and the S2/S3 dependency gate was materially released.

No Wave 6 production deployment has occurred. Production client/API identities and rollback points remain those recorded above.
