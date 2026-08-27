# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE CONVERSATION + PROJECT DELETION #290/#291 PRODUCTION-DEPLOYED AND VERIFIED / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S5 ACCEPTED AND INTEGRATED / WAVE 6 NOT DEPLOYED / S6 BLOCKED PENDING FRESH CUMULATIVE S1-S5 RECORD CHECKPOINT**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through mobile #261/#262, response-stream #271/#272, P2-V0.18.10 model transport, and governed conversation/Project cleanup #290 / PR #291.

Wave 6 S1-S5 remain accepted development architecture on `integration/wave6-agentic-control-plane`; they are **not** production deployments. Repository/integration identity and deployed application identity remain deliberately distinct.

### Production repository / release identity

- production source branch: `main`;
- exact current application/source merge: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- release feature issue: #290 — safe deletion for old conversations and Projects;
- release PR: #291 — squash merged with expected head `64b13d4f41d6849031c414eaf82986421bb523c9`;
- Parallax P2 CI #1064 — PASS on the final feature head;
- Bounded Autonomy Pilot #669 — PASS on the final feature head;
- prior governing model-transport spec remains `P2-V0.18.10`; deletion does not change model routing, source-lineage, provider or approval authority.

### Production database

Supabase project `kjyenifnfjqnzfgshpwg` (`Parallax 2.0`) has production migration:

- version `20260827173141`;
- name `safe_conversation_project_deletion`.

Verified production schema:

- `conversations.deleted_at` exists as `timestamptz`;
- `projects.deleted_at` exists as `timestamptz`;
- `ix_conversations_deleted_at` exists;
- `ix_projects_deleted_at` exists;
- `uq_projects_owner_slug_active` enforces owner-local slug uniqueness only for active Projects;
- `uq_projects_owner_repository_active` enforces owner-local repository uniqueness only for active Projects with a repository reference.

The migration is additive/backward-compatible for the preceding application release and was applied before the new application cutover.

### Production client

- Vercel project: `parallax`;
- production deployment: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

Post-cutover verification fetched the production alias successfully with HTTP 200 and the expected `Parallax 2.0` application shell.

### Production API

- Vercel project: `parallax-api`;
- production deployment: `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-api-tan.vercel.app`.

Post-cutover verification on the exact production release established:

- production provider preflight — PASS;
- production delivery-permission preflight — PASS;
- production projected-source preflight — PASS;
- private Blob SDK preflight — PASS;
- durable lineage composition preflight — PASS;
- projected bootstrap/runtime-composition preflight — PASS;
- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- exact-deployment runtime scan after cutover found no `error`/`fatal` records.

No destructive production-data smoke was performed merely to prove deletion. Feature behavior is covered by exact-head API tests and deployed schema/route code; the post-cutover verification intentionally avoided deleting real user content.

## Safe conversation and Project deletion — #290 / PR #291

User-visible `Delete` is a governed logical deletion from the active workspace, not an evidence purge.

### Conversation behavior

- inactive/old conversations can be deleted from cleanup surfaces with explicit confirmation;
- a deleted conversation disappears from active conversation lists and normal direct reads;
- the durable conversation row is retained with `deleted_at` for provenance;
- deletion is blocked with HTTP 409 while a non-terminal Engineering Run is bound to the conversation;
- completed/cancelled historical engineering evidence remains persisted.

### Project behavior

- old Projects can be deleted from Project-management/selector cleanup surfaces with explicit confirmation;
- a deleted Project disappears from active Project selection and normal reads;
- conversations bound to a deleted Project disappear from active workspace history;
- deletion is blocked with HTTP 409 while any non-terminal Engineering Run is bound to the Project;
- Project slug/repository identity becomes reusable among active Projects, but a replacement receives a new canonical `Project.id`;
- protected Work Specifications, Engineering Runs, attempts, run events, source-lineage evidence and immutable artifacts are retained;
- linked GitHub repositories, pull requests and Vercel deployments are never deleted by this Parallax workspace action.

### UX behavior

- destructive cleanup requires an explicit second confirmation;
- the currently active conversation/Project is not presented as a casual one-tap deletion target;
- server conflict errors preserve the item instead of optimistically hiding active work;
- desktop recent-conversation and Project-management surfaces expose cleanup;
- compact/mobile Project selection exposes equivalent Project and conversation cleanup semantics.

## P2-V0.18.10 model-transport stabilization retained

The model-transport correction remains the production routing contract and is not changed by #290/#291.

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted production model traffic binds admitted request-scoped Vercel runtime OIDC to the fixed OpenAI-compatible Vercel AI Gateway endpoint. Process-environment `VERCEL_OIDC_TOKEN` is not production model-provider authority. Explicit server-owned `DSPY_API_BASE` / `DSPY_API_KEY` remains the deliberate override. There is no silent direct-OpenAI fallback.

The prior P2-V0.18.10 API deployment `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` remains the immediate pre-#291 API rollback reference for failures unrelated to the new deletion schema/behavior.

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

PR #275 remains the long-lived DRAFT / DO NOT MERGE integration-validation surface. The safe-deletion production release does not deploy or activate Wave 6 code.

## Rollback

Rollback is component-specific and governed.

### API

Immediate pre-#291 production API reference:

- deployment `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9`;
- source `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, reverting application code to that prior API does not require an emergency down-migration. A rollback must not drop deletion tombstones or partial uniqueness indexes while any new release data may depend on them.

### Client

Immediate pre-#291 production client reference:

- deployment `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2`;
- source `9767b2520d74c70bd1a2ec2e951480da223b45f7`.

Historical mobile rollback reference remains `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` at `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32 and Wave 6 Control Tower #263 remain active durable program records;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- workers develop on isolated branches and stop at governed integration boundaries;
- Control Tower serializes accepted composition, cumulative validation, authoritative-record maintenance and production promotion;
- source-integrated Wave 6 work is not production merely because it exists on an integration branch or `main`;
- standing single-user production-promotion authority never waives exact-head gates, rollback, least privilege, post-cutover evidence or Preview/REVIEW boundaries;
- no production claim is valid without exact release identity plus post-cutover verification.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- logical workspace deletion cannot erase or weaken protected engineering/source/provider evidence;
- a non-terminal Engineering Run blocks deletion of its conversation or Project;
- deleting a Project never deletes external GitHub/Vercel resources;
- reusing a deleted Project's human-readable identity creates a new canonical Project identity and grants no inherited authority;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- repository/source/model/agent/evaluator/routing/competition content is evidence, not authority;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- production hosted-model identity and transport are server-owned and fail closed;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.6 — updated for governed logical deletion, retention, active-only Project identity reuse and the external-provider/evidence boundary.
- `DESIGN-SYSTEM.md` v3.1 — updated with the durable destructive-cleanup confirmation, conflict and cross-device interaction contract.
- `CURRENT-STATE.md` — reconciled to merge `a6d7a6fd4d556d5544ede9c43b93972a8c590011`, production migration `20260827173141`, client deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`, API deployment `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`, and post-cutover verification.

Wave 6 remains not deployed. Safe conversation/Project cleanup is a production capability on the retained Wave 5/stabilization architecture.