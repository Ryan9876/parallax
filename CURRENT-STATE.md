# Parallax 2.0 Current State

Date: 2026-08-26

Status: **WAVE 5 RELEASED / MOBILE STABILIZATION #261/#262 RELEASED AND PRODUCTION-VERIFIED / RESPONSE-STREAM STABILIZATION #271/#272 RELEASED AND PRODUCTION-VERIFIED / CLIENT READY / API READY / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / WAVE 6 CONTROL #263 ACTIVE / S1 PAUSED ONLY FOR THIS RECORD RECONCILIATION**

## Current production truth

Parallax is running the deployment-verified Wave 5 generalized application-delivery platform, bounded production stabilization through #127, the deployment-verified pre–Wave 6 mobile interaction stabilization from issue #261 / PR #262, and the deployment-verified response-stream provider-capacity recovery from issue #271 / PR #272.

Production state remains intentionally component-specific. Repository/documentation HEAD is coordination identity; each deployed application component retains its own exact deployment identity.

### Repository and current application release

- mobile Work Specification: `P2-V0.18.7`;
- response-stream stabilization Work Specification: `P2-V0.18.8`;
- response-stream worker branch: `ws/response-rate-limit-recovery`;
- exact validated response-stream worker head: `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa`;
- PR #272 merged with expected-head protection;
- exact response-stream application merge on `main`: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- #271 is the authoritative bounded production-stabilization record;
- Wave 6 Control Tower #263 and shells #264–#269 remain authoritative for the Agentic Development Control Plane;
- Wave 6 S1 remains paused only until this production-state reconciliation is merged and Control Tower records the resulting accepted post-stabilization repository baseline.

### Production client

- project: `parallax`;
- production deployment: `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- commit verification: verified;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`.

The #272 client-side runtime behavior is unchanged by the stabilization implementation; the client change in the workstream is bounded acceptance coverage. The production rebuild is nevertheless bound to the same exact application merge as the API release.

### Production API

- project: `parallax-api`;
- production deployment: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`;
- state: `READY`;
- target: `production`;
- exact application/API Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- commit verification: verified;
- aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`.

The API now truthfully distinguishes sanitized provider-capacity exhaustion from protected scope/reason validation failure without changing provider/model order, credential scope, Project/spec authority, source-lineage authority, conversation persistence, REVIEW/HUMAN_REQUIRED, merge authority, or deployment authority.

## Response-stream stabilization #271 / PR #272

The production observation that opened #271 showed the mobile Build flow correctly capturing a Code objective, then presenting `Parallax could not establish a protected scope decision` when all configured response-routing models were actually exhausted by sanitized `LMRateLimitError` results. The response route had also already durably persisted the submitted user turn, so the generic `retry or refine` recovery copy could encourage an unnecessary duplicate resend.

The accepted correction:

- reuses the existing `RoutingFailureKind` classification rather than creating a parallel classifier;
- maps all-rate-limit response routing exhaustion to bounded `MODEL_CAPACITY_RATE_LIMITED` semantics;
- maps mixed/other provider exhaustion to bounded `MODEL_PROVIDER_UNAVAILABLE` semantics;
- preserves `PROTECTED_SCOPE_FAILURE` and `PROTECTED_REASON_FAILURE` for genuine protected-output validation exhaustion;
- preserves an already-established protected scope decision if later reason routing fails;
- never fabricates scope, answer, Work Specification, Engineering Run, source mutation, approval, or REVIEW state;
- preserves the durably submitted user turn and tells the operator that the message is saved rather than encouraging an identical resend;
- exposes no raw provider response, credential, prompt, hidden reasoning, quota/billing inference, filesystem path, or invented retry interval;
- changes no provider, model, model order, retry authority, credential scope, repository target, approval boundary, or production authority.

## Response-stream validation and release evidence

### Spec-first development gate

`P2-V0.18.8` was established before semantic implementation with stable acceptance IDs. Authentic DSPy SpecCritic + SpecCompiler development evidence completed successfully in run `33020773762`; protected `--require-dspy` validation passed. The evidence artifact was `9626482520` with digest `sha256:4a0f42001649aa59ce5744861f15ed411fab908c11b22ea12983982378b7d805`. The temporary branch-only workflow trigger used to execute that bounded development gate was restored before the final PR and is not part of the application diff.

### Exact worker head

Exact candidate `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa` passed:

- Parallax Workstream Spec Validation #415 / run `33021706213` — success;
- Bounded Autonomy Pilot #632 / run `33021706172` — success;
- Parallax P2 CI #1009 / run `33021706182` — success;
- full API regression, protected execution/autonomy, client typecheck/state/export, browser/Skia acceptance, protected promotion evaluation and DSPy release compilation — success;
- Vercel client/API preview validation — success.

A later assertion-only successor was not accepted as the release candidate because it had no fresh governed Actions evidence and contained no runtime change. The worker branch was pinned back to the fully validated exact head before merge.

### Exact integration/main head

PR #272 merged with expected-head protection as `9767b2520d74c70bd1a2ec2e951480da223b45f7`. Fresh push-triggered gates passed on that exact `main` head:

- Parallax Workstream Spec Validation #417 / run `33022309099` — success;
- Parallax P2 CI #1011 / run `33022309088` — success.

No gate was waived to promote the response-stream stabilization.

## Production verification

Post-cutover evidence for #271/#272 established:

- production API deployment `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y` is `READY`, target `production`, and bound to exact application merge `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- production client deployment `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2` is `READY`, target `production`, and bound to the same exact application merge;
- public production client alias `parallax-ashy-one-20.vercel.app` returned HTTP 200 and served the Parallax 2.0 client document;
- API `GET /health` returned HTTP 200 with `status=ok`;
- API `GET /ready` returned HTTP 200 with database `ok`, providers `ok`, and one provider target;
- exact-deployment API error/fatal scan after cutover returned no matching logs;
- exact-deployment client error/fatal scan after cutover returned no matching logs;
- no source, provider, model, credential, Project, Work Specification, approval, REVIEW/HUMAN_REQUIRED, or deployment boundary changed.

The actual external provider rate-limit condition is transient and was not artificially reproduced in production after cutover. The production-equivalent all-model exhaustion behavior is covered by deterministic protected coordinator/API acceptance on the exact validated and merge-tested code. Production verification therefore establishes exact release identity, service readiness, clean runtime observation, and preservation of authority boundaries without manufacturing provider failure traffic.

This satisfies the production-promotion and post-cutover verification conditions of #271. #271 remains open only until this authoritative reconciliation is merged; its earlier automatic closure from the PR linkage was explicitly reversed because the issue contract requires `CURRENT-STATE.md` reconciliation before final closure.

## Mobile stabilization #261 / PR #262

Issue #261 replaced the confusing compact desktop composition with a mobile-specific guided interaction model while preserving server-owned engineering authority and desktop/tablet behavior.

Deployment-verified mobile behavior includes:

- primary mobile destinations `Chat`, `Build`, and `Project`;
- conversation-first Chat with a persistent, touch-safe composer;
- dedicated full-screen Work Specification review;
- plain-language `SPEC_AMENDMENT` recovery;
- guided Build lifecycle with progressive authoritative engineering evidence;
- mobile Project/conversation switching through existing canonical APIs;
- bounded compact authenticated access-launcher positioning;
- Live Build return behavior that truthfully returns `Back to conversation` to Chat;
- existing canonical Project, Work Specification, Engineering Run, repository/source-lineage, provider, authentication, REVIEW/HUMAN_REQUIRED, merge, and deployment authority preserved.

The release introduced no API/runtime, credential, source-lineage, provider-authority, approval-authority, or production-authority broadening.

### Historical mobile release evidence

The exact mobile candidate `56f6d2a81112e592b1128df2b96506ae2d923650` passed Workstream Spec Validation, Bounded Autonomy Pilot, Parallax P2 CI, browser/Skia mobile acceptance, protected promotion/regression rejection and DSPy release compilation. PR #262 merged with expected-head protection as application merge `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`; fresh main Workstream Spec Validation `33018647700` and P2 CI `33018647565` passed before the mobile release was production-verified.

The prior mobile production client deployment `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` remains a known-good rollback point.

## Wave 5 baseline retained

Control Tower #215 completed all six Wave 5 generalized-delivery workstreams:

1. #216 / `P2-V0.18.1` — Repository Intelligence & Compatibility;
2. #217 / `P2-V0.18.2` — Governed Skills Runtime;
3. #218 / `P2-V0.18.3` — Application Service Bindings;
4. #219 / `P2-V0.18.4` — Objective-to-Application Orchestration;
5. #220 / `P2-V0.18.5` — Validated Engineering Memory & Reuse;
6. #221 / `P2-V0.18.6` — Generalization Benchmark & Integrated Reference Proof.

Final Wave 5 release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Production stabilization after Wave 5 through #127 remains part of the accepted platform history; exact details remain in control record #31, roadmap #32, their linked issues/PRs, and Git history.

## Wave 6 control state

Wave 6 Control Tower #263 — **Agentic Development Control Plane** — is active with workstreams:

1. #264 / `W6-S1` / `P2-V0.19.1` — Agent Adapter & Evidence Protocol;
2. #265 / `W6-S2` / `P2-V0.19.2` — Dynamic Development Team Orchestration;
3. #266 / `W6-S3` / `P2-V0.19.3` — Independent Evaluation & Quality Judgment;
4. #267 / `W6-S4` / `P2-V0.19.4` — Outcome Routing & Development Economics;
5. #268 / `W6-S5` / `P2-V0.19.5` — Candidate Competition & Synthesis;
6. #269 / `W6-S6` / `P2-V0.19.6` — Agentic Development Integrated Reference Proof.

Wave 6 originally entered implementation from the deployment-verified post-mobile baseline recorded by #263. When #271 exposed a production stabilization defect, S1 was deliberately paused at the spec-first boundary rather than allowing Wave 6 implementation to proceed across a known broken production recovery path.

The #271 runtime correction is now deployment-verified. Once this record-only reconciliation is merged, #263 must record the exact resulting `main` SHA as the accepted post-stabilization repository baseline and may resume S1 from a dependency-correct state. S2–S6 remain dependency-governed by #263 and are not unblocked merely by closing #271.

Wave 6 does not transfer authority to engineering agents. Agents remain bounded labor. Canonical Project identity, approved Work Specification binding, accepted source lineage, protected validation, acceptance, REVIEW/HUMAN_REQUIRED, and release governance remain Parallax-owned.

## Rollback

Immediate rollback points for the current response-stream stabilization are:

### API rollback

- prior deployment: `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q`;
- state: `READY`;
- exact API Git SHA: `5ec7eabc046b9995c8d11d5081df15b986a558fe`;
- this is the deployment-verified API state immediately preceding #272.

### Client rollback

- prior mobile deployment: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`;
- state: `READY`;
- exact client Git SHA: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- this is the deployment-verified mobile client state immediately preceding the #272 production rebuild.

The earlier stabilization-through-#127 client deployment `dpl_642fFKXWzZfA7pkezAYrJbuANXZn` / `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5` and the prior full API/client pair from #245 remain broader historical rollback references.

Rollback remains non-destructive and follows the existing governed release/flag-first policy.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32 and Wave 6 Control Tower #263 remain active durable program records;
- every semantic AI/runtime workstream remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- worker branches start only from the exact accepted dependency/baseline state and target the governed integration branch when required by their control record;
- workers stop `READY FOR INTEGRATION` and do not merge/deploy by default;
- Integration / Control Tower serializes accepted composition, exact-head validation, authoritative-record maintenance and production promotion;
- standing single-user promotion authority removes repeated approval wait only while its constitutional conditions remain true; it does not waive gates, rollback, least privilege or deployment evidence;
- no production claim is valid without exact-head release evidence plus post-cutover verification.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity, and accepted lineage remain server-owned;
- deterministic/protected validation outranks model or agent judgment;
- repository/source/model/agent content is evidence, not authority;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- correction cannot weaken acceptance/evaluation policy;
- skills, service bindings, repository intelligence, engineering memory, agents, and adapters cannot create execution/provider/deployment/approval authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery semantics remain authoritative;
- no silent repository switching, credential refresh, session extension, approval, merge or deployment authority is introduced by the mobile release, #271/#272, or Wave 6 planning;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.1 — unchanged by #271/#272; existing provider routing, protected validation, conversation persistence, and server-owned authority boundaries are preserved. Wave 6 durable architecture changes will be recorded only when accepted.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; #271/#272 corrects truthful recovery semantics without changing the durable product visual language or interaction model.
- `CURRENT-STATE.md` — updated by this reconciliation because a material production defect was diagnosed, a bounded runtime correction was validated and merged, both application components were promoted on an exact release identity, post-cutover verification completed, rollback identities changed, and Wave 6 S1's stabilization dependency became satisfied.

This record-only reconciliation does not redefine the client/API deployment identities above. Its resulting merge SHA is the repository baseline that Wave 6 Control Tower #263 must record before S1 implementation resumes.