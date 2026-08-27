# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 RELEASED / MOBILE STABILIZATION #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM STABILIZATION #271/#272 PRODUCTION-VERIFIED / AI GATEWAY PROVIDER STABILIZATION #284/#287 DEPLOYED AND INFRASTRUCTURE-VERIFIED / CAPTURE SPEC OPERATOR SMOKE PENDING / CLIENT READY / API READY / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / WAVE 6 CONTROL #263 ACTIVE**

## Current production truth

Parallax is running the deployment-verified Wave 5 generalized application-delivery platform, bounded production stabilization through #127, the deployment-verified mobile interaction stabilization from issue #261 / PR #262, the deployment-verified response-stream provider-capacity recovery from issue #271 / PR #272, and the newly deployed API provider-boundary correction from issue #284 / PR #287.

Production state remains intentionally component-specific. Repository/documentation HEAD is coordination identity; each deployed application component retains its own exact deployment identity. The #284/#287 API release is deployed and infrastructure/readiness verified, but authenticated end-to-end Capture Spec verification is still pending one operator smoke request and is not yet claimed complete.

### Repository and current application release

- mobile Work Specification: `P2-V0.18.7`;
- response-stream stabilization Work Specification: `P2-V0.18.8`;
- AI Gateway provider-boundary Work Specification: `P2-V0.18.9`;
- #284 worker branch: `p2/provider-gateway-stabilization`;
- exact validated #284 worker head: `37f20330f03072532eebd7eca5ec9cd1f9efab4f`;
- PR #287 merged with expected-head protection;
- exact current API application merge on `main`: `74a027a69dbc6f983e2023e9e5367f2d5fd0bd7b`;
- #284 is the authoritative provider-boundary stabilization record and remains open until authenticated Capture Spec smoke plus final record reconciliation complete;
- Wave 6 Control Tower #263 remains authoritative for the Agentic Development Control Plane; its live dependency/integration state is controlled by #263 and is not superseded by this production record.

### Production client

- project: `parallax`;
- production deployment: `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- commit verification: verified;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`.

The #284/#287 stabilization is API-only. Vercel intentionally canceled/ignored the corresponding client production rebuild because no deployable client path changed, so the existing deployment-verified client artifact remains authoritative.

### Production API

- project: `parallax-api`;
- production deployment: `dpl_C5sdDZgnwq8uSKFkA7DkJc4rCW82`;
- state: `READY`;
- target: `production`;
- exact application/API Git SHA: `74a027a69dbc6f983e2023e9e5367f2d5fd0bd7b`;
- commit verification: verified;
- aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`.

The API now selects Vercel AI Gateway as the hosted DSPy transport boundary whenever bounded Gateway authentication is available, while preserving canonical Parallax model identity/order, explicit trusted DSPy development overrides, protected validation, conversation persistence, Project/spec/source-lineage authority, REVIEW/HUMAN_REQUIRED, merge authority, and deployment authority.

## AI Gateway provider-boundary stabilization #284 / PR #287

### Production observation and diagnosis

An authenticated Capture Spec request returned HTTP 429 after Luna -> Terra -> Sol each ended in sanitized `LMRateLimitError`. Operator checks established that Vercel AI Credit remained available, Anthropic Claude succeeded through the Vercel AI Gateway playground, and OpenAI GPT-5.6 Terra also succeeded through that same Gateway. The differentiator was therefore the Parallax application transport path rather than a general Gateway, credit, or Terra outage.

The accepted diagnosis was that `build_lm()` constructed DSPy/LiteLLM models using canonical `openai/...` identities without deterministically selecting the Vercel AI Gateway provider namespace in hosted production. Unless an explicit DSPy endpoint override happened to exist, LiteLLM could therefore use the direct OpenAI provider path even though Parallax production is hosted on Vercel and the operator's usable AI credit is on Vercel AI Gateway.

### Accepted correction

The #284/#287 correction:

- preserves canonical `ModelRouter.MODEL_ORDER` exactly as Luna -> Terra -> Sol;
- preserves canonical public/evidence model identities as `openai/gpt-5.6-*`;
- keeps explicit `DSPY_API_BASE` / `DSPY_API_KEY` as the highest-priority trusted development/CI override;
- otherwise resolves hosted Gateway authentication in deterministic order: `AI_GATEWAY_API_KEY`, `VERCEL_AI_GATEWAY_API_KEY`, then `VERCEL_OIDC_TOKEN`;
- internally maps hosted OpenAI transport to LiteLLM's documented `vercel_ai_gateway/openai/...` namespace;
- preserves existing direct/local behavior if neither an explicit DSPy override nor Gateway authentication exists;
- does not log, persist, serialize, expose to prompts, or return the selected credential;
- adds no Anthropic/Google fallback and changes no provider/model order, retry authority, Project/spec/source-lineage authority, REVIEW boundary, merge authority, or deployment authority.

### Spec-first and exact-head evidence

`P2-V0.18.9` was established before semantic implementation with stable AC-01 through AC-12. Authentic DSPy SpecCritic + SpecCompiler development evidence completed successfully in run `33037450807`; protected `--require-dspy` validation passed. Evidence artifact `9632572627` has digest `sha256:20ea10e0aa5d8657d6c173370fdd3acb078957243b994fbc6629d041c368ce33`. The exact compiled plan byte digest is `sha256:495eda192b82f5c85a9ead5bd2e8b8b5d2575a7ee1c6da4530d78427d272338e`. The temporary branch-local DSPy workflow change was restored byte-for-byte and is absent from the final application diff.

Exact worker head `37f20330f03072532eebd7eca5ec9cd1f9efab4f` passed:

- Workstream Spec Validation #454 / run `33037858893` — success;
- Bounded Autonomy #660 / run `33037858820` — success;
- P2 CI #1050 / run `33037858812` — success, including focused Gateway routing tests, full API/contracts, client/browser/Skia, protected promotion evaluation and DSPy release compilation;
- Vercel `parallax` and `parallax-api` Preview commit statuses — success;
- exact API Preview `dpl_7YQRgZSfNgEduoEPmY5z9JqCiMs5` — `READY`, bound to the exact worker head.

PR #287 merged with expected-head protection as application merge `74a027a69dbc6f983e2023e9e5367f2d5fd0bd7b`.

### Production deployment verification completed so far

Post-cutover evidence establishes:

- production API deployment `dpl_C5sdDZgnwq8uSKFkA7DkJc4rCW82` is `READY`, target `production`, and bound to exact application merge `74a027a69dbc6f983e2023e9e5367f2d5fd0bd7b`;
- production build provider, delivery-permission, projected-source, private-Blob, lineage-composition, bootstrap, execution-snapshot and run-event schema preflights passed;
- API `GET /health` returned HTTP 200 with `status=ok`;
- API `GET /ready` returned HTTP 200 with database `ok`, providers `ok`, and one provider target;
- exact-deployment API error/fatal scan after cutover returned no matching logs;
- the production client remains the prior deployment-verified artifact because this release changed no client path.

Authenticated Capture Spec has not yet been replayed after this cutover. Therefore this record intentionally distinguishes **deployed + infrastructure/readiness verified** from **Capture Spec end-to-end production-verified**. One authenticated operator smoke request and corresponding exact-deployment log inspection are still required before #284 closes and before the provider-boundary correction is described as fully production-verified.

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
- exposes no raw provider response, credential, prompt, hidden reasoning, quota/billing inference, filesystem path, or invented Retry-After interval;
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

## Historical #271 production verification

Post-cutover evidence for #271/#272 established:

- production API deployment `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y` was `READY`, target `production`, and bound to exact application merge `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- production client deployment `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2` is `READY`, target `production`, and bound to the same exact application merge;
- public production client alias `parallax-ashy-one-20.vercel.app` returned HTTP 200 and served the Parallax 2.0 client document;
- API `GET /health` returned HTTP 200 with `status=ok`;
- API `GET /ready` returned HTTP 200 with database `ok`, providers `ok`, and one provider target;
- exact-deployment API error/fatal scan after cutover returned no matching logs;
- exact-deployment client error/fatal scan after cutover returned no matching logs;
- no source, provider, model, credential, Project, Work Specification, approval, REVIEW/HUMAN_REQUIRED, or deployment boundary changed.

The actual external provider rate-limit condition was transient and was not artificially reproduced after that cutover. Production-equivalent all-model exhaustion behavior was covered by deterministic protected coordinator/API acceptance on exact validated and merge-tested code. Issue #271 is closed completed.

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

Wave 6 Control Tower #263 — **Agentic Development Control Plane** — remains active with workstreams #264 through #269. Its live accepted dependency and integration state is governed by #263 and the Wave 6 integration branch, not by stale snapshots in this production record.

At this reconciliation, Control Tower has recorded accepted/integrated S1-S4 and has released S5 semantic development under #268; S6 remains dependency-governed and no Wave 6 production deployment has occurred. Before any Wave 6 production promotion, the integration branch must reconcile the accepted #284/#287 provider-boundary correction from `main` so Wave 6 cannot regress production model transport back to the direct OpenAI path.

Wave 6 does not transfer authority to engineering agents. Agents remain bounded labor. Canonical Project identity, approved Work Specification binding, accepted source lineage, protected validation, acceptance, REVIEW/HUMAN_REQUIRED, and release governance remain Parallax-owned.

## Rollback

Immediate rollback points for the current API provider-boundary stabilization are:

### API rollback

- prior production deployment: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`;
- state: `READY` at its release time;
- exact API Git SHA: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- this is the deployment-verified API state immediately preceding #287 and remains the immediate application rollback identity if the new Gateway transport fails authenticated smoke verification.

### Client rollback

- current production client remains `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2` at `9767b2520d74c70bd1a2ec2e951480da223b45f7` because #287 was API-only;
- prior mobile deployment `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` at `2bd677c3532df9fc436cac39cd23c4ca86f6e26d` remains the broader mobile rollback point.

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
- no silent repository switching, credential refresh, session extension, approval, merge or deployment authority is introduced by the mobile release, #271/#272, #284/#287, or Wave 6 planning;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.1 — pending durable provider-boundary reconciliation after authenticated Capture Spec smoke confirms the deployed transport behavior; no architectural record is being changed merely from a deployment that still has one required functional verification outstanding.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; #284/#287 changes no durable visual language or interaction model.
- `CURRENT-STATE.md` — updated by this reconciliation because #284/#287 is now generated, validated, merged, deployed, health/readiness verified and rollback-bound, while truthfully recording that authenticated Capture Spec end-to-end verification remains pending.

This record-only reconciliation does not redefine the component deployment identities above. A final authenticated Capture Spec smoke, exact-deployment log confirmation, #284 closure and durable architecture reconciliation remain the next release-record actions.