# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / FINAL SAFE-DELETION ACCEPTANCE PENDING AUTHENTICATED POST-CUTOVER SMOKE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 ACCEPTED AND INTEGRATED / CUMULATIVE S1-S6 CHECKPOINT VALIDATED / WAVE 6 NOT DEPLOYED / RELEASE AUDIT FOUND LIVE RUNTIME-ACTIVATION GAP / #304 P2-V0.19.7 SPEC-FIRST CLOSURE ACTIVE / PRODUCTION PROMOTION BLOCKED PENDING RUNTIME ACTIVATION + RELEASE PROOF**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through mobile #261/#262, response-stream #271/#272 and P2-V0.18.10 model transport.

Safe conversation/Project deletion originated in #290 / PR #291 and is present in production with migration `20260827173141`. The post-merge lifecycle/authorization audit gaps were corrected under `P2-V0.18.12` / PR #294. PR #294 merged to `main` as `109444dcd7e13bfe842dea71355607941258b073` after the exact corrective implementation head passed all required gates. Vercel deployed the corrective API SHA to production and the production alias is serving it. The client had no source delta, so its main deployment was intentionally canceled by the configured Ignored Build Step and the existing verified client artifact remains active.

The corrective release is **production-deployed and infrastructure-verified but not yet accepted as fully deployment-verified feature behavior** because the final authenticated post-cutover deletion smoke cannot be executed by the available connector without an application user session. No destructive smoke will be performed against real user content merely to manufacture release evidence.

Wave 6 S1-S6 are accepted development architecture and are **not** production deployments. The production-synchronized S1-S5 checkpoint was extended by accepted S6 worker head `75d6a51f8d014e70772a54f032370ead64c965bb`, merged through PR #300 into `integration/wave6-agentic-control-plane` as `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`. Exact worker gates Workstream #485, Bounded Autonomy #692 and P2 CI #1096 passed, followed by fresh cumulative integration-head Workstream #486, Bounded Autonomy #693 and P2 CI #1097. Temporary validation PR #302 was closed without merge to `main`; production remains unchanged.

Whole-product release audit then found a material activation gap: the Wave 6 delta provides accepted S1-S6 protocols/decision layers/reference proof, but ordinary `EngineeringRuntimeComposition` / `AutonomyCoordinator` does not yet invoke the S1-S5 agentic control plane during a normal build. Shipping that state would deploy validated primitives without fulfilling the operator-facing Wave 6 runtime objective. Control Tower therefore opened #304 / `P2-V0.19.7` as a required runtime-activation release closure. No Wave 6 production promotion is authorized until that closure is integrated and release-qualified.

### Safe-deletion release identity

- production source branch: `main`;
- initial feature merge: `a6d7a6fd4d556d5544ede9c43b93972a8c590011` from PR #291;
- corrective merge: `109444dcd7e13bfe842dea71355607941258b073` from PR #294;
- feature issue/workstream: #290 — safe deletion for old conversations and Projects;
- corrective specification: `P2-V0.18.12`;
- pre-implementation Workstream Spec Validation #463 — PASS on spec head `095803846b5bf1c51aa62eb79ffc66665a33134c`;
- final corrective Workstream Spec Validation #471 — PASS;
- final corrective Bounded Autonomy Pilot #680 — PASS;
- final corrective Parallax P2 CI #1078 — PASS;
- exact final corrective implementation head before merge: `3f49d1b5fa7ff41bd89303c92db897030a82247d`.

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

The migration is additive/backward-compatible and does not require a corrective migration for P2-V0.18.12.

### Production client

- Vercel project: `parallax`;
- active verified deployment retained from #291: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- state: `READY`;
- target: `production`;
- artifact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

The corrective main commit `109444dcd7e13bfe842dea71355607941258b073` created client deployment `dpl_9mkVu5nKgza9YnbbFYf1N4hMdmx9`, which Vercel canceled because the configured Ignored Build Step (`git diff --quiet HEAD^ HEAD ./`) found no deployable client-root changes. This is expected for the API-only correction and intentionally preserves the existing verified client artifact rather than manufacturing a redundant client build.

### Production API — corrective P2-V0.18.12

- Vercel project: `parallax-api`;
- production deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `109444dcd7e13bfe842dea71355607941258b073`;
- public production alias: `parallax-api-tan.vercel.app`.

Post-cutover verification on the corrective deployment established:

- production alias is serving deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- exact corrective deployment runtime scan found no `error`/`fatal` records;
- unauthenticated `GET /v1/conversations` → HTTP 401 with `Authentication required`, confirming the protected route remains behind the authentication boundary.

The final authenticated destructive-behavior smoke is intentionally still open: the available deployment connector cannot present a Parallax application user session, and production verification must not be faked by weakening auth or deleting real user data without a deliberate test target.

## Safe deletion corrective hardening — P2-V0.18.12 / PR #294

PR #294 is **MERGED**. The corrective implementation:

1. derives conversation and Project deletion terminality from the protected Engineering Run `TERMINAL_STAGES` contract instead of a duplicated deletion lifecycle list;
2. treats `COMPLETE`, `SPEC_AMENDMENT` and `CANCELLED` as terminal while preserving `FAILED` and all other states outside the protected terminal set as deletion-blocking;
3. propagates authenticated application role into conversation deletion;
4. requires application `owner` role to delete a historical unbound conversation while preserving compatibility read visibility;
5. preserves canonical Project-bound cross-owner not-found behavior;
6. adds focused regression tests for lifecycle parity, owner-only unbound destructive authority, evidence retention and Project identity reuse.

### Remaining release acceptance item

The exact corrective implementation, merge, production API deployment, health/readiness checks, authentication boundary and error scan are verified. The only remaining #290 completion item is an authenticated post-cutover feature smoke against a deliberately disposable conversation/Project test target. Until that evidence exists, #290 remains open and the feature is not labeled fully deployment-verified.

## Durable deletion contract

- user-visible `Delete` is logical workspace deletion, not evidence purge;
- deleted conversations/Projects disappear from active workspace reads;
- protected Work Specifications, Engineering Runs, attempts, run events, source lineage and immutable evidence remain retained;
- linked GitHub repositories, pull requests and Vercel deployments are never deleted by workspace cleanup;
- any relevant Engineering Run outside authoritative protected `TERMINAL_STAGES` blocks deletion with HTTP 409;
- deleted Project slug/repository identities may be reused among active Projects, but replacement creates a new canonical `Project.id` and gains no inherited authority;
- Project-bound deletion derives ownership from canonical Project identity and fails closed across owners;
- historical unbound conversation read compatibility does not grant destructive authority; deletion requires application `owner` role;
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
Authoritative integration branch: `integration/wave6-agentic-control-plane`.  
Current accepted S1-S6 integration head: `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`.  
Current production baseline: `main@a455b223ad4707aa7fe2ccd3470a5e7640c40da2`.  
Wave 6 production deployment: **none**.

### Accepted cumulative S1-S6 evidence

- accepted production-synchronized S1-S5 checkpoint: `f8b5bcd9b40f13777c16e3d323030b814dc4fa86`;
- S6 authorized record parent: `fed6662c0d7d228b714c31237ec5088076b9a2aa`;
- S6 exact validated worker head: `75d6a51f8d014e70772a54f032370ead64c965bb`;
- S6 canonical PR #300: **MERGED TO INTEGRATION ONLY**;
- resulting cumulative integration head: `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`;
- S6 worker Workstream Spec Validation #485 — **PASS**;
- S6 worker Bounded Autonomy Pilot #692 — **PASS**;
- S6 worker Parallax P2 CI #1096 — **PASS**;
- cumulative integration Workstream Spec Validation #486 — **PASS**;
- cumulative integration Bounded Autonomy Pilot #693 — **PASS**;
- cumulative integration Parallax P2 CI #1097 — **PASS**;
- temporary main-targeted validation PR #302: **CLOSED WITHOUT MERGE**;
- long-lived PR #275 remains **DRAFT / DO NOT MERGE** and is not a production release candidate.

Accepted/integrated semantic state:

1. #264 / S1 Agent Adapter & Evidence Protocol — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / S2 Dynamic Development Team Orchestration — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / S3 Independent Evaluation & Quality Judgment — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / S4 Outcome Routing & Development Economics — **COMPLETE / ACCEPTED / INTEGRATED**;
5. #281 repository source-tree capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / S5 Candidate Competition & Synthesis — **COMPLETE / ACCEPTED / INTEGRATED**;
7. #269 / S6 Agentic Development Integrated Reference Proof — **COMPLETE / ACCEPTED / INTEGRATED**.

### Release-closure decision — #304 / P2-V0.19.7

After S1-S6 integration, a whole-product audit compared the accepted Wave 6 objective with the actual integration diff and live runtime composition. The accepted Wave 6 production-code delta adds the agent protocol, team orchestration, independent judgment, routing/economics, competition/synthesis and integrated reference proof, but does not modify the ordinary `EngineeringRuntimeComposition`, `AutonomyCoordinator` or `ProtectedImplementationRuntime` path to invoke those decisions for a normal Engineering Run.

That gap is material: deploying `01dda9f...` would make the primitives importable and validated but would not make the normal Parallax build flow automatically select/manage one or more agents. Control Tower therefore treats Wave 6 as **integrated but not production-release-qualified**.

#304 / `W6-R1` / `P2-V0.19.7` is the required closure workstream. Its branch is `p2/w6-runtime-activation`, based exactly on `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`. It is spec-first and must activate the accepted S1-S5 decision plane inside the existing single-writer protected Engineering Run/source-lineage/BUILD/TEST/VERIFY/Preview/REVIEW path without inventing a second authority path. Production promotion remains blocked until #304 is validated, accepted, integrated, record-reconciled and separately release-verified.

## Rollback

Rollback is component-specific and governed.

### API

Corrective production API:

- deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- source `109444dcd7e13bfe842dea71355607941258b073`.

Previous #291 API rollback candidate:

- deployment `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 accepted API reference remains `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` at `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while deletion data may depend on them.

### Client

Active safe-deletion client artifact:

- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 client reference remains `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2` at `9767b2520d74c70bd1a2ec2e951480da223b45f7`. Historical mobile rollback reference remains `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` at `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32, safe-deletion workstream #290 and Wave 6 Control Tower #263 remain active durable program records;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- workers develop on isolated branches and stop at governed integration boundaries;
- interacting production workstreams are serialized at shared lifecycle/record boundaries;
- a production-baseline sync into an undeployed future-wave integration branch must preserve accepted future-wave semantics, use current production records for production truth, and pass fresh cumulative exact-head gates before becoming the new integration checkpoint;
- standing single-user production-promotion authority never waives exact-head gates, rollback, least privilege, post-cutover evidence or Preview/REVIEW boundaries;
- path-aware ignored builds may preserve a previously verified component artifact when a release has no changes under that component root;
- deployed/infrastructure-ready is not equivalent to deployment-verified feature behavior when a required post-cutover feature smoke is still absent;
- no production-verification claim is valid without exact release identity plus appropriate post-cutover evidence.

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
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.7 — current production architecture plus accepted Wave 6 S1-S5 durable architecture; the synchronization/release decision introduces no new durable architecture contract.
- `DESIGN-SYSTEM.md` v3.1 — current production design system; the synchronization/release decision introduces no new design contract.
- `CURRENT-STATE.md` — updated after cumulative S1-S5 validation and non-force integration advancement to record the accepted checkpoint, exact gate evidence, unchanged production state and S6 spec-first release boundary.

Wave 6 remains not deployed. Safe deletion corrective code is serving in production; final safe-deletion feature acceptance remains deliberately open until authenticated post-cutover deletion behavior is exercised against a disposable test target. S6 may begin spec-first work, but semantic implementation remains gated by an approved `P2-V0.19.6` and authentic DSPy compiled evidence.