# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED WITH FINAL AUTHENTICATED DELETION SMOKE STILL OPEN / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 + W6-R1 #304 ACCEPTED, INTEGRATED, DEPLOYED AND RELEASE-VERIFIED / WAVE 6 RELEASE #312 AUTHENTICATED PRODUCTION PROOF PASS ON main@55066fcc / PREVIEW READY / REVIEW CEILING PROVEN / REPLAY IDENTITIES STABLE**

## Current production truth

Production is cumulative through the fully release-verified Wave 6 API runtime on exact application source `main@55066fccfcb9b4d645cdb87c8b7d061f032d6dec`. The production API deployment is `dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj`, state `READY`, target `production`, serving `parallax-api-tan.vercel.app`.

The Wave 6 production release is now **DEPLOYMENT-VERIFIED**. A fresh authenticated Project-bound Engineering Run exercised the live server-owned agentic path through PLAN, IMPLEMENT, exact-lineage BUILD/TEST/VERIFY, bounded GitHub/Vercel Preview delivery and the operator-controlled REVIEW stop. The exact same autonomous operation was replayed and preserved attempt count, delivery identity, run-event identity, revision and worker identity without duplicate canonical mutation or Preview publication. No merge or production promotion was performed by the runtime proof.

The client had no Wave 6 production source delta and therefore retains its prior verified production artifact under the path-aware ignored-build contract.

Safe conversation/Project deletion remains present in production with migration `20260827173141` and corrective P2-V0.18.12 hardening. That feature is production-deployed and infrastructure-verified, but its final authenticated destructive-behavior smoke remains intentionally open because no disposable authenticated production target has been established. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

## Production release identities

### Production API — Wave 6 final verified state

- Vercel project: `parallax-api`;
- production source branch: `main`;
- exact application Git SHA: `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- production deployment: `dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj`;
- state: `READY`;
- target: `production`;
- public production alias: `parallax-api-tan.vercel.app`;
- version-controlled activation: `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`.

Production deployment evidence:

- provider/source authority preflight — PASS;
- exact repository-scoped delivery-permission preflight — PASS;
- projected-source preflight — PASS;
- private Blob read/write and immutable lineage composition — PASS;
- selected-candidate artifact exact round trip — PASS;
- projected Engineering Runtime bootstrap — PASS;
- process recreation and replay preflight — PASS;
- no-stage-mutation and rollback verification — PASS;
- deny-all execution-snapshot restoration and offline dependency verification — PASS;
- run-event schema guard — PASS;
- `GET /health` → HTTP 200;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- exact-deployment error/fatal scan after the final authenticated proof — clean.

### Production client

- Vercel project: `parallax`;
- active verified deployment retained from #291: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- state: `READY`;
- target: `production`;
- artifact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

Wave 6 release corrections changed API runtime behavior only. Client production remained on the verified artifact rather than manufacturing a redundant production build.

### Production database

Supabase project `kjyenifnfjqnzfgshpwg` (`Parallax 2.0`) retains production migration:

- version `20260827173141`;
- name `safe_conversation_project_deletion`.

Verified schema remains:

- `conversations.deleted_at` as `timestamptz`;
- `projects.deleted_at` as `timestamptz`;
- `ix_conversations_deleted_at`;
- `ix_projects_deleted_at`;
- `uq_projects_owner_slug_active` for owner-local active slug uniqueness;
- `uq_projects_owner_repository_active` for owner-local active repository uniqueness.

The migration is additive/backward-compatible.

## Wave 6 — Agentic Development Control Plane

Control Tower: #263.  
Authoritative integration branch: `integration/wave6-agentic-control-plane`.  
Accepted runtime-activated integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`.  
Current verified production application source: `main@55066fccfcb9b4d645cdb87c8b7d061f032d6dec`.  
Current production API deployment: `dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj` — **READY / DEPLOYMENT-VERIFIED**.  
Production activation flag: **enabled through version-controlled `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`**.

### Accepted S1-S6 + W6-R1 state

1. #264 / S1 Agent Adapter & Evidence Protocol — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
2. #265 / S2 Dynamic Development Team Orchestration — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
3. #266 / S3 Independent Evaluation & Quality Judgment — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
4. #267 / S4 Outcome Routing & Development Economics — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
5. #281 repository source-tree capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
6. #268 / S5 Candidate Competition & Synthesis — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
7. #269 / S6 Agentic Development Integrated Reference Proof — **COMPLETE / ACCEPTED / INTEGRATED / DEPLOYED**;
8. #304 / W6-R1 Runtime Activation — **COMPLETE / VALIDATED / ACCEPTED / INTEGRATED / DEPLOYMENT-VERIFIED**.

### Durable Wave 6 authority contract

- ordinary protected PLAN uses one server-owned agentic planning seam bound to exact Project/run/approved Work Specification/acceptance/source identity;
- S2 selects the smallest adequate admitted team; operator agent selection is not part of the normal build path;
- agent work is non-authoritative candidate labor;
- candidate BUILD/TEST/VERIFY executes on disposable deny-all Vercel Sandbox materializations before independent evaluation;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- S4 routing consumes provenance-bound evidence and S5 cannot select a failed or unvalidated candidate;
- exactly one selected candidate reaches `ProtectedImplementationRuntime`;
- `ProtectedImplementationRuntime` remains the single canonical source writer and authoritative IMPLEMENT transition owner;
- selected-candidate artifacts are private immutable replay evidence only and must be rebound/revalidated before canonical mutation;
- only accepted lineage reaches protected BUILD/TEST/VERIFY and source delivery;
- Preview is the ordinary autonomous publication ceiling;
- REVIEW remains operator-controlled;
- agentic runtime cannot merge or production-deploy ordinary Project output.

### Wave 6 release #312 closure evidence

Initial release sequence retained:

- release candidate PR #313 exact head: `3d90bbedfeca16a1d0dcf4e564dde6832fa0085d`;
- qualified release merge: `a5c700762bcf8ebbd5605d7e5d47756bab10fb4e`;
- source-tree parity correction #314 / PR #315: `8bd124244f9bb8175c417e4c4084cc15d9bea066`;
- API source-root correction #316 / PR #318: `bafda5b3d42ca3662a075cefb8c83bd9b017392e`;
- service-runtime canary correction #319 / PR #321 worker: `ce55f9c4fabd82774954007483997b9d52878e2c`;
- first infrastructure-verified Wave 6 production checkpoint: `831fef94aa1c94ff1178b1a325e8774d49fd8752` / `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`.

Final production-proof corrections:

- protected S3 evidence correction merged through PR #334, producing production `0759757d08cd9ba9cd54d82dc415d072618e33f3`;
- bounded Vercel Preview terminal-read correction PR #337 merged as `4b7539eb51d1aa6b7a0202249158fe4356599481`;
- post-delivery canonical run-refresh correction PR #341 merged as final application source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- PR #341 exact validated head: `1c71cbf732921c53fdea21627adae137dcf54710`;
- Bounded Autonomy Pilot #736 / run `33132235288` — PASS;
- Parallax P2 CI #1151 / run `33132235282` — PASS, including full API regression, client typecheck, browser/Skia acceptance, protected promotion evaluation and DSPy release compilation;
- exact-head API Preview `dpl_3iYdkNFpDqLgNVDL6fTQchw359Jj` — READY;
- final production deployment `dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj` — READY;
- final production `/health` and `/ready` — HTTP 200;
- final production exact-deployment error/fatal scan — clean.

### Final authenticated production proof

Validation-only proof branch head: `22aee7e5c60f4811c83096c3b0c1c427cf829bee`.  
Validation deployment: `dpl_95Djhv5wVaPLS21JzR1xZY7n9m2r` — **READY**.  
The validation branch differs from exact production only by the pre-existing validation harness and has no application-runtime drift.

Fresh authenticated production Engineering Run:

- Project-bound run: `a1cb0f62-b1af-4d6b-b88c-140d2583cade`;
- exact production source: `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- accepted lineage: `src:39b11769ca7e7c7cc8370601c1567a7c59878877c4b2906796e2473d7c7752f8`;
- parent lineage: `src:ab1b0c80fb40e54dd4d4d073e95a2e208d8c8b8bf80ba54f44cc0ac6305ee075`;
- protected stages passed: PLAN, IMPLEMENT, BUILD, TEST, VERIFY;
- exact accepted mutation: `apps/client/w4-final-source-delivery-proof.txt`;
- selected candidate: `candidate-primary`;
- review PR: #343, base exact `main@55066fcc...`, exactly one changed file / one added line;
- delivery branch: `parallax/b1f6984d-a1cb0f62`;
- delivery commit: `4912a06d73f5b6e383edd167e3bf7ca3ed8c74cc`;
- bounded client Preview: `dpl_2nU5zSPpeeZ5dEhfXiEg5kZV3PNC` — `READY`;
- final Engineering Run state: `REVIEW`;
- stop reason: `REVIEW_REQUIRED`;
- final revision: `6`;
- event count: `15`;
- worker state: `READY_FOR_INTEGRATION`;
- replay attempt count stable: **true**;
- replay delivery identity stable: **true**;
- replay event identity stable: **true**;
- replay revision stable: **true**;
- replay worker identity stable: **true**;
- candidate source-lineage/run/review/production authority claims remained false;
- production merge or promotion performed by proof: **false**.

This satisfies release #312's final authenticated runtime and replay acceptance contract. Wave 6 may now be called **DEPLOYMENT-VERIFIED**.

Proof-generated PR #343 remains an operator-review artifact. It is not a production promotion and must not be merged merely because the release proof passed.

## Safe deletion corrective hardening — P2-V0.18.12 / PR #294

Safe deletion remains production-deployed with the following durable contract:

- user-visible `Delete` is logical workspace deletion, not evidence purge;
- deleted conversations/Projects disappear from active workspace reads;
- protected Work Specifications, Engineering Runs, attempts, run events, source lineage and immutable evidence remain retained;
- linked GitHub repositories, pull requests and Vercel deployments are never deleted by workspace cleanup;
- any relevant Engineering Run outside authoritative protected `TERMINAL_STAGES` blocks deletion with HTTP 409;
- deleted Project slug/repository identities may be reused among active Projects, but replacement creates a new canonical `Project.id` and gains no inherited authority;
- Project-bound deletion derives ownership from canonical Project identity and fails closed across owners;
- historical unbound conversation read compatibility does not grant destructive authority; deletion requires application `owner` role;
- destructive UI actions require explicit confirmation and do not hide state until server success.

Remaining #290 acceptance item: an authenticated post-cutover destructive-behavior smoke against a deliberately disposable conversation/Project target. Until that evidence exists, safe deletion remains **production-deployed and infrastructure-verified**, not fully feature deployment-verified.

## P2-V0.18.10 model-transport stabilization retained

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted production model traffic binds admitted request-scoped Vercel runtime OIDC to the fixed OpenAI-compatible Vercel AI Gateway endpoint. Process-environment `VERCEL_OIDC_TOKEN` is not production model-provider authority. Explicit server-owned `DSPY_API_BASE` / `DSPY_API_KEY` remains the deliberate override. There is no silent direct-OpenAI fallback.

## Deployment-verified stabilization retained

### Mobile #261 / PR #262

The mobile release remains deployment-verified. It provides mobile primary destinations `Chat`, `Build`, and `Project`; conversation-first Chat; full-screen Work Specification review; `SPEC_AMENDMENT` recovery; guided Build lifecycle; canonical Project/conversation switching; compact authenticated access behavior; and Live Build return-to-chat semantics while preserving server-owned authority.

Historical identities retained:

- exact validated worker: `56f6d2a81112e592b1128df2b96506ae2d923650`;
- application merge: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- known-good mobile client rollback: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`.

### Response-stream #271 / PR #272

The response-stream correction remains deployment-verified. It distinguishes provider-capacity exhaustion from protected scope/reason validation failure, preserves the durably submitted user turn, and does not change model/provider order, credentials, Project/spec/source authority, approval or REVIEW boundaries.

Historical identities retained:

- exact validated worker: `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa`;
- application merge: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- historical API deployment: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`.

## Wave 5 baseline retained

Control Tower #215 completed generalized application delivery through #216-#221 / `P2-V0.18.1`-`P2-V0.18.6`. Final Wave 5 application release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Later stabilization, safe deletion and Wave 6 are cumulative and do not replace its authority model.

## Next governed implementation boundary

Local-first model-routing PR #303 / issue #301 remains an **isolated validated candidate / DO NOT MERGE / DO NOT DEPLOY** until its explicit integration conditions are satisfied.

Wave 6 deployment verification now satisfies the first prerequisite for that workstream. Before any integration of #303:

1. this `CURRENT-STATE.md` release closure must be accepted on `main`;
2. #303 must be reconciled onto the exact accepted current production source rather than its pre-Wave-6 parent;
3. architecture drift/conflicts must be resolved without weakening Wave 6 authority contracts;
4. authentic spec/evaluation evidence and all required exact-head gates must be rerun on the reconciled candidate;
5. Control Tower must explicitly authorize integration;
6. production deployment remains a separate governed action after integration acceptance.

Do not merge #303 merely because Wave 6 is now verified.

## Rollback

Rollback is component-specific and governed.

### API

Current fully verified Wave 6 production API:

- deployment `dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj`;
- source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`.

Immediate previous Wave 6 production artifact:

- deployment `dpl_9yxeJmYCJa7sAEYgNZZcKKFjmzmb`;
- source `4b7539eb51d1aa6b7a0202249158fe4356599481`;
- infrastructure checks passed, but its final proof exposed the stale post-delivery response/replay-parity defect corrected by PR #341; do not label it fully release-verified.

Conservative pre-Wave-6 application rollback reference:

- deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- source `109444dcd7e13bfe842dea71355607941258b073`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while deletion data may depend on them. Wave 6 activation configuration must roll back with the selected application source/configuration rather than via an untracked manual toggle.

### Client

Active client artifact:

- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 client reference remains `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2` at `9767b2520d74c70bd1a2ec2e951480da223b45f7`. Historical mobile rollback reference remains `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` at `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32, safe-deletion workstream #290 and Wave 6 Control Tower #263 remain durable program records;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- workers develop on isolated branches and stop at governed integration boundaries;
- interacting production workstreams are serialized at shared lifecycle/record boundaries;
- a production-baseline sync into an undeployed future-wave branch must preserve accepted semantics and pass fresh cumulative exact-head gates before becoming an accepted checkpoint;
- standing single-user production-promotion authority never waives exact-head gates, rollback, least privilege, post-cutover evidence or Preview/REVIEW boundaries;
- server-owned activation flags do not redefine generated/integrated code as deployed;
- path-aware ignored builds may preserve a previously verified component artifact when a release has no changes under that component root;
- deployed/infrastructure-ready is not equivalent to deployment-verified feature behavior when required post-cutover evidence is absent;
- no production-verification claim is valid without exact release identity plus appropriate post-cutover evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- agentic planning/dispatch/candidate evidence cannot advance canonical lineage or durable Engineering Run authority directly;
- selected-candidate artifact persistence is immutable replay evidence only and must be rebound/revalidated before canonical mutation;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- production hosted-model identity and transport are server-owned and fail closed;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- deleting a Project never deletes external GitHub/Vercel resources;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; Wave 6 release verification and the replay-envelope correction create no new constitutional authority.
- `ARCHITECTURE.md` v3.9 — unchanged; the final corrections enforce already-recorded delivery/replay contracts rather than changing architecture.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; no durable visual or interaction-language contract changed.
- `CURRENT-STATE.md` — reconciled to exact Wave 6 production source/deployment and the final authenticated Project-bound release proof.

Wave 6 is fully deployment-verified on `main@55066fccfcb9b4d645cdb87c8b7d061f032d6dec`. Safe deletion remains production-deployed/infrastructure-verified with its authenticated destructive smoke deliberately open. Local-first routing remains isolated pending reconciliation, fresh evidence, gates and explicit Control Tower integration authorization.
