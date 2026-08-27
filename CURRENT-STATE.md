# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION #291 + CORRECTIVE P2-V0.18.12/#294 DEPLOYED AND INFRASTRUCTURE-VERIFIED / AUTHENTICATED DELETION SMOKE PENDING / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S5 ACCEPTED AND INTEGRATED / WAVE 6 NOT DEPLOYED / S6 BLOCKED PENDING FRESH CUMULATIVE S1-S5 RECORD CHECKPOINT**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through mobile #261/#262, response-stream #271/#272 and P2-V0.18.10 model transport.

Safe conversation/Project deletion from #290 is present in production. Initial PR #291 introduced the logical-deletion schema/API/client behavior at merge `a6d7a6fd4d556d5544ede9c43b93972a8c590011`. Corrective P2-V0.18.12 / PR #294 then hardened the deletion lifecycle and destructive authorization at merge `109444dcd7e13bfe842dea71355607941258b073`. The corrective API deployment is READY, production `/health` and `/ready` pass, the protected unauthenticated conversation boundary still returns 401, and the exact deployment has no error/fatal runtime records in the post-cutover scan.

The feature is **deployed and infrastructure-verified but not yet accepted as fully deployment-verified feature behavior** because one live authenticated deletion smoke from the production UI remains outstanding. Exact-head tests already prove the 204/403/404/409 deletion contracts without risking real production data.

Wave 6 S1-S5 remain accepted development architecture on `integration/wave6-agentic-control-plane`; they are **not** production deployments. The deletion workstream remains on the current production line and does not activate Wave 6.

### Corrective application identity

- production source branch: `main`;
- current corrective application merge: `109444dcd7e13bfe842dea71355607941258b073`;
- corrective validated worker head: `3f49d1b5fa7ff41bd89303c92db897030a82247d`;
- feature issue/workstream: #290 — safe deletion for old conversations and Projects;
- initial release PR: #291 — merged at `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- corrective PR: #294 — merged from exact validated head `3f49d1b5fa7ff41bd89303c92db897030a82247d` onto latest main;
- corrective governing spec: `P2-V0.18.12`;
- Workstream Spec Validation #471 — PASS on the final corrective head;
- Bounded Autonomy Pilot #680 — PASS on the final corrective head;
- Parallax P2 CI #1078 — PASS on the final corrective head.

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

The migration is additive/backward-compatible and must not be destructively rolled back while safe-deletion tombstones or identity reuse may depend on it.

### Production client

The corrective hardening changed no client source. The existing #291 client remains the production client:

- Vercel project: `parallax`;
- production deployment: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

Vercel created but cancelled the no-client-change production build for corrective merge `109444dcd7e13bfe842dea71355607941258b073`; this is not represented as a deployed client artifact. The live production alias continues to return HTTP 200 with the expected `Parallax 2.0` application shell.

### Corrective production API

- Vercel project: `parallax-api`;
- corrective production deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `109444dcd7e13bfe842dea71355607941258b073`;
- public production alias: `parallax-api-tan.vercel.app`.

Corrective build and post-cutover evidence established:

- production provider preflight — PASS;
- production delivery-permission preflight — PASS;
- production projected-source preflight — PASS;
- private Blob SDK preflight — PASS;
- durable lineage composition preflight — PASS;
- projected bootstrap/runtime-composition preflight — PASS;
- production execution-snapshot preflight — PASS;
- production run-event schema guard — PASS;
- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- unauthenticated `GET /v1/conversations` → HTTP 401 `Authentication required`;
- exact-deployment runtime error/fatal scan after cutover found no matching records.

Initial #291 API deployment `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP` remains a rollback candidate while the final authenticated deletion smoke is pending.

## Safe deletion corrective hardening — P2-V0.18.12 / PR #294

PR #294 is **MERGED / DEPLOYED / INFRASTRUCTURE-VERIFIED**. The corrective implementation resolved both post-#291 audit findings.

### Engineering Run terminal-state parity

Conversation and Project deletion guards now derive terminality from the protected Engineering Run runtime's authoritative `TERMINAL_STAGES` contract rather than carrying an independent deletion-specific list. The current terminal set is `COMPLETE`, `SPEC_AMENDMENT`, and `CANCELLED`.

Focused exact-head tests prove:

- `SPEC_AMENDMENT` does not block conversation or Project deletion;
- `FAILED` remains non-terminal and blocks deletion with HTTP 409;
- deletion helper state exactly matches the protected runtime contract, preventing silent lifecycle drift.

### Historical unbound destructive authorization

Historical unbound conversations intentionally retain compatibility read visibility because they predate canonical Project ownership. Corrective #294 separates that compatibility read visibility from destructive authority:

- application `owner` role is required to delete a historical unbound conversation;
- non-owner DELETE returns HTTP 403 without mutation while ordinary compatibility read remains unchanged;
- Project-bound conversation and Project deletion continue to derive ownership from canonical Project identity and fail closed as not found across owners.

### Remaining acceptance gate

All implementation, merge, database, deployment and infrastructure gates are complete. One acceptance item remains before the feature is called fully deployment-verified and #290 is closed:

1. perform one authenticated production deletion of a genuinely old, non-current conversation or inactive Project through the existing production UI;
2. confirm the item disappears from active history/selection and the UI remains healthy;
3. inspect exact production API runtime logs for the deletion request and any error/fatal records;
4. reconcile `CURRENT-STATE.md` to final deployment-verified status and close #290 completed.

## Intended durable deletion contract

The architecture/design records describe the durable contract the corrective release now implements:

- user-visible `Delete` is logical workspace deletion, not evidence purge;
- deleted conversations/Projects disappear from active workspace reads;
- protected Work Specifications, Engineering Runs, attempts, run events, source lineage and immutable evidence remain retained;
- linked GitHub repositories, pull requests and Vercel deployments are never deleted by workspace cleanup;
- any relevant Engineering Run outside authoritative protected `TERMINAL_STAGES` blocks deletion with HTTP 409;
- deleted Project slug/repository identities may be reused among active Projects, but replacement creates a new canonical `Project.id` and gains no inherited authority;
- historical unbound conversation deletion requires application `owner` role while compatibility read visibility remains unchanged;
- Project-bound destructive ownership derives from canonical Project identity;
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

Immediate safe-deletion rollback candidate:

- deployment `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 accepted API reference remains:

- deployment `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9`;
- source `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while deletion data may depend on them.

### Client

The current safe-deletion client is still #291:

- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

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
- deployed is not equivalent to deployment-verified while the authenticated safe-deletion smoke remains outstanding;
- no production-verification claim is valid without exact release identity plus post-cutover feature evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- logical workspace deletion cannot erase or weaken protected engineering/source/provider evidence;
- authoritative Engineering Run lifecycle state, not a duplicated deletion-specific list, decides whether a run is terminal;
- historical compatibility read visibility does not imply destructive authorization;
- historical unbound conversation deletion is restricted to application owner role until a separate durable ownership model exists;
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
- `ARCHITECTURE.md` v3.6 — records the durable governed logical-deletion/retention, evidence-retention, active-run and external-provider boundaries. A final refinement to explicitly record protected `TERMINAL_STAGES` derivation and owner-only historical-unbound destructive authorization remains appropriate with final feature acceptance.
- `DESIGN-SYSTEM.md` v3.1 — records explicit destructive-cleanup confirmation, server-conflict and cross-device semantics; no corrective design-system change is required.
- `CURRENT-STATE.md` — updated to record corrective P2-V0.18.12 / PR #294 as merged and exact API deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex` as READY/infrastructure-verified while authenticated production deletion smoke remains pending.

Wave 6 remains not deployed. Safe deletion is deployed with corrective hardening, but remains pending one authenticated feature smoke before full deployment-verification acceptance and closure of #290.
