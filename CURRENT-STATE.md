# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION #291 DEPLOYED BUT NOT YET ACCEPTED AS DEPLOYMENT-VERIFIED / CORRECTIVE P2-V0.18.12 / PR #294 ACTIVE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S5 ACCEPTED AND INTEGRATED / WAVE 6 NOT DEPLOYED / S6 BLOCKED PENDING FRESH CUMULATIVE S1-S5 RECORD CHECKPOINT**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through mobile #261/#262, response-stream #271/#272 and P2-V0.18.10 model transport.

Safe conversation/Project deletion from #290 / PR #291 is **present in production** at merge `a6d7a6fd4d556d5544ede9c43b93972a8c590011`, with the required additive database migration applied and both client/API deployments READY. It is **not yet accepted as deployment-verified feature behavior** because post-merge audit found two correctness/authority gaps now owned by corrective `P2-V0.18.12` / PR #294.

Wave 6 S1-S5 remain accepted development architecture on `integration/wave6-agentic-control-plane`; they are **not** production deployments. The deletion workstream remains on the current production line and does not activate Wave 6.

### Deployed #291 application identity

- production source branch: `main`;
- deployed application merge: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- feature issue/workstream: #290 — safe deletion for old conversations and Projects;
- initial release PR: #291 — squash merged from validated head `64b13d4f41d6849031c414eaf82986421bb523c9`;
- Parallax P2 CI #1064 — PASS on the final #291 feature head;
- Bounded Autonomy Pilot #669 — PASS on the final #291 feature head.

### Production database

Supabase project `kjyenifnfjqnzfgshpwg` (`Parallax 2.0`) has production migration:

- version `20260827173141`;
- name `safe_conversation_project_deletion`.

Verified schema:

- `conversations.deleted_at` exists as `timestamptz`;
- `projects.deleted_at` exists as `timestamptz`;
- `ix_conversations_deleted_at` exists;
- `ix_projects_deleted_at` exists;
- `uq_projects_owner_slug_active` enforces owner-local slug uniqueness only for active Projects;
- `uq_projects_owner_repository_active` enforces owner-local repository uniqueness only for active Projects with a repository reference.

The migration is additive/backward-compatible and must not be destructively rolled back while the corrective release is in progress.

### Production client for #291

- Vercel project: `parallax`;
- deployment: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

The production alias returned HTTP 200 with the expected `Parallax 2.0` application shell.

### Production API for #291

- Vercel project: `parallax-api`;
- deployment: `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-api-tan.vercel.app`.

Post-cutover infrastructure/runtime evidence established:

- production provider preflight — PASS;
- production delivery-permission preflight — PASS;
- production projected-source preflight — PASS;
- private Blob SDK preflight — PASS;
- durable lineage composition preflight — PASS;
- projected bootstrap/runtime-composition preflight — PASS;
- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- exact-deployment runtime scan after cutover found no `error`/`fatal` records.

This proves the #291 application and migration are deployed and infrastructure-ready. It does not override the post-merge deletion correctness findings below.

## Safe deletion corrective hardening — P2-V0.18.12 / PR #294

Workstream #290 is **ACTIVE / CORRECTIVE VALIDATION**. Corrective branch `ws/safe-deletion-hardening` and PR #294 are limited to deletion lifecycle parity, historical-unbound destructive authorization, focused tests and later release-record reconciliation.

### Gap 1 — Engineering Run terminal-state drift

The deployed #291 deletion guard duplicated terminal run states as only `COMPLETE` and `CANCELLED`. The protected Engineering Run runtime owns `TERMINAL_STAGES`, which also contains `SPEC_AMENDMENT`. Therefore the deployed #291 guard can incorrectly return HTTP 409 for a conversation/Project whose relevant run is already terminal `SPEC_AMENDMENT`.

Corrective acceptance requires deletion guards to derive from the authoritative protected runtime terminal-state contract rather than carrying an independent lifecycle list. `FAILED`, `REVIEW`, `PLAN` and other states outside protected `TERMINAL_STAGES` remain non-terminal and must continue to block deletion.

### Gap 2 — historical unbound destructive authorization

Historical unbound conversations intentionally retain compatibility read visibility because they predate canonical Project ownership. The initial DELETE path reused that visibility without a separate durable ownership identity.

Corrective acceptance therefore requires application `owner` role for destructive deletion of a historical unbound conversation. Compatibility read visibility remains unchanged. Project-bound conversation and Project deletion continue to derive ownership from canonical Project identity and fail closed across owners.

### Corrective acceptance gate

The safe-deletion feature is not marked deployment-verified until all of the following are true:

1. `P2-V0.18.12` spec validation passes;
2. the exact corrective implementation head passes Workstream Spec Validation, Bounded Autonomy and P2 CI;
3. merge uses expected-head protection after latest-main collision review;
4. production deployment is tied to the exact corrective merged SHA;
5. `/health`, `/ready`, runtime-error scans and authenticated deletion behavior are verified after cutover;
6. `CURRENT-STATE.md` is reconciled to the verified corrective release and #290 is closed completed.

## Intended durable deletion contract

The architecture/design records now describe the durable contract the corrective release must satisfy:

- user-visible `Delete` is logical workspace deletion, not evidence purge;
- deleted conversations/Projects disappear from active workspace reads;
- protected Work Specifications, Engineering Runs, attempts, run events, source lineage and immutable evidence remain retained;
- linked GitHub repositories, pull requests and Vercel deployments are never deleted by workspace cleanup;
- any relevant Engineering Run outside authoritative protected `TERMINAL_STAGES` blocks deletion with HTTP 409;
- deleted Project slug/repository identities may be reused among active Projects, but replacement creates a new canonical `Project.id` and gains no inherited authority;
- historical unbound conversation deletion requires application `owner` role;
- destructive UI actions require explicit confirmation and do not hide state until server success.

## P2-V0.18.10 model-transport stabilization retained

The model-transport correction remains the accepted production routing contract and is unaffected by safe-deletion hardening.

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted production model traffic binds admitted request-scoped Vercel runtime OIDC to the fixed OpenAI-compatible Vercel AI Gateway endpoint. Process-environment `VERCEL_OIDC_TOKEN` is not production model-provider authority. Explicit server-owned `DSPY_API_BASE` / `DSPY_API_KEY` remains the deliberate override. There is no silent direct-OpenAI fallback.

The prior accepted P2-V0.18.10 API deployment `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` remains an application rollback reference for failures unrelated to the already-applied deletion schema.

## Deployment-verified stabilization retained

### Mobile #261 / PR #262

The mobile release remains deployment-verified. It provides mobile primary destinations `Chat`, `Build`, and `Project`; conversation-first Chat; full-screen Work Specification review; `SPEC_AMENDMENT` recovery; guided Build lifecycle; canonical Project/conversation switching; compact authenticated access behavior; and Live Build return-to-chat semantics while preserving server-owned authority.

Historical mobile identities retained:

- exact validated worker: `56f6d2a81112e592b1128df2b96506ae2d923650`;
- application merge: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- known-good mobile client rollback: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`.

### Response-stream #271 / PR #272

The response-stream correction remains deployment-verified. It distinguishes provider-capacity exhaustion from protected scope/reason validation failure, preserves the durably submitted user turn, and does not change model/provider order, credentials, Project/spec/source authority, approval or REVIEW boundaries.

Historical accepted identities retained:

- exact validated worker: `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa`;
- application merge: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- historical API deployment: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`.

## Wave 5 baseline retained

Control Tower #215 completed generalized application delivery through #216-#221 / `P2-V0.18.1`-`P2-V0.18.6`. Final Wave 5 application release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Later production stabilization and workspace cleanup are cumulative and do not replace its authority model.

## Wave 6 — Agentic Development Control Plane

Control Tower: #263.  
Integration branch: `integration/wave6-agentic-control-plane`.  
Current accepted S1-S5 functional integration head: `9fe751a96ec050545abdcfbb016c668cd4c7336f`.  
Wave 6 production deployment: **none**.

Accepted/integrated state remains:

1. #264 / S1 Agent Adapter & Evidence Protocol — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / S2 Dynamic Development Team Orchestration — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / S3 Independent Evaluation & Quality Judgment — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / S4 Outcome Routing & Development Economics — **COMPLETE / ACCEPTED / INTEGRATED**;
5. #281 repository source-tree capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / S5 Candidate Competition & Synthesis — **COMPLETE / ACCEPTED / INTEGRATED**;
7. #269 / S6 — **BLOCKED pending authoritative S5 record reconciliation on the integration branch plus a fresh cumulative exact-head S1-S5 gate**.

PR #275 remains the long-lived DRAFT / DO NOT MERGE integration-validation surface. Safe-deletion hardening does not deploy or activate Wave 6 code.

## Rollback

Rollback is component-specific and governed.

### API

Pre-#291 accepted API reference:

- deployment `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9`;
- source `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while #291/#294 data may depend on them.

### Client

Pre-#291 client reference:

- deployment `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2`;
- source `9767b2520d74c70bd1a2ec2e951480da223b45f7`.

Historical mobile rollback reference remains `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` at `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32, safe-deletion workstream #290 and Wave 6 Control Tower #263 remain active durable program records;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- workers develop on isolated branches and stop at governed integration boundaries;
- interacting production workstreams are serialized at shared lifecycle/record boundaries;
- standing single-user production-promotion authority never waives exact-head gates, rollback, least privilege, post-cutover evidence or Preview/REVIEW boundaries;
- deployed is not equivalent to deployment-verified when corrective acceptance gaps remain;
- no production-verification claim is valid without exact release identity plus post-cutover feature evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- logical workspace deletion cannot erase or weaken protected engineering/source/provider evidence;
- authoritative Engineering Run lifecycle state, not a duplicated deletion-specific list, decides whether a run is terminal;
- historical compatibility read visibility does not imply destructive authorization;
- deleting a Project never deletes external GitHub/Vercel resources;
- reusing a deleted Project's human-readable identity creates a new canonical Project identity and grants no inherited authority;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- production hosted-model identity and transport are server-owned and fail closed;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.6 — records the durable governed logical-deletion/retention, evidence-retention, active-run and external-provider boundaries. Corrective #294 aligns implementation to the authoritative Engineering Run lifecycle and destructive authorization contract.
- `DESIGN-SYSTEM.md` v3.1 — records explicit destructive-cleanup confirmation, server-conflict and cross-device semantics introduced by the feature; no additional design-system change is required for corrective #294.
- `CURRENT-STATE.md` — corrected after post-merge audit to distinguish #291 as deployed/infrastructure-ready from deployment-verified feature acceptance; P2-V0.18.12 / PR #294 remains active until exact corrective deployment verification succeeds.

Wave 6 remains not deployed. Safe deletion is present in production but remains under corrective acceptance and must not be represented as fully deployment-verified until #294 completes its governed release gate.