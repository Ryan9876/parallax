# Parallax 2.0 Architecture

Version: 3.11
Status: Authoritative

## Version relationship

Architecture v3.11 is a bounded architectural update to v3.10, not a platform rewrite. The complete v3.10 architecture at repository commit `edcac5abc2b1a920d460a15ec3ec81aa2909884f` is incorporated by reference. Every v3.10 durable contract that is not explicitly changed below remains authoritative, including canonical Project/Work Specification/Engineering Run authority, immutable accepted source lineage, single-writer IMPLEMENT mutation, durable worker recovery, deny-all Sandbox validation, Wave 6 agentic orchestration/evaluation/routing/competition boundaries, project-scoped tool/provider authority, logical workspace deletion/retention, protected evaluation, Preview/REVIEW ceilings, governed release evidence, and accepted `P2-V0.19.8` local-first model routing.

This version records the accepted Wave 7 development architecture through W7-S5 (`P2-V0.20.1`–`P2-V0.20.5`). These capabilities are integrated on `integration/wave7-productization` at `00a9e66e2f87a1f992d375b4217845b8f072e11d`; they are not thereby merged to `main` or production-deployed. Production truth remains separately authoritative in `CURRENT-STATE.md`.

## Current system shape

Parallax remains a universal Expo / React Native client backed by a Python FastAPI intelligence service, PostgreSQL/Supabase persistence, private immutable object storage, Vercel Sandbox isolation and bounded external-provider adapters.

The authority flow remains:

```text
Authenticated principal
      ↓
Canonical Project.id + approved Work Specification
      ↓
Engineering Run + accepted source lineage
      ↓
server-owned planning / optional Wave 6 agentic orchestration
      ↓
non-authoritative candidate work
      ↓
deny-all candidate validation + independent evaluation
      ↓
ProtectedImplementationRuntime
      ↓
single-writer safe mutation + lineage CAS acceptance
      ↓
exact-lineage BUILD / TEST / VERIFY
      ↓
GitHub branch/PR + Vercel Preview
      ↓
protected evaluation
      ↓
operator REVIEW
```

Wave 6 S1–S6 plus W6-R1 are production-deployed and release-verified. Agent planning, team orchestration, evaluation, routing, competition and selected-candidate replay evidence remain orchestration/evidence layers only; they do not gain direct Project/spec, Engineering Run transition, source-head, provider-administration, merge, production-deployment or REVIEW authority.

## Wave 7 productization architecture

Wave 7 adds productization and measured-autonomy layers around the existing canonical authority model. Through S5, it does not create a second execution state machine, source authority, provider authority, deployment authority or REVIEW bypass.

### W7-S1 — ParallaxBench

ParallaxBench is a read-only objective-evaluation layer. It consumes bounded development/evaluation evidence and produces comparison evidence for protected promotion decisions. Benchmark or model judgment cannot override deterministic/protected failure, mutate an Engineering Run, accept source, administer providers/tools, deploy, merge or complete REVIEW.

### W7-S2 — Agent Run projection and control contract

The Agent Run projection is a typed projection over the existing server-owned Engineering Run, attempts, run events, worker recovery and evaluation/delivery evidence. It does not create a second run state machine.

Projection identity is bound to canonical Project, run, approved Work Specification revision/digest and acceptance IDs. Projection controls are limited to already-authorized server-side pause/resume/cancel operations and require the current Project/run/revision/state contract. The client cannot supply source lineage, provider authority or lifecycle truth through this surface.

Observed, estimated and unknown economic values remain distinct; an unknown value is not represented as zero.

### W7-S3 — Agent Run Canvas / Development Studio

The Development Studio composes the accepted S2 server-owned projection/control contract into the client. The client may present canonical run state/evidence and request existing bounded server operations; it cannot become canonical state authority.

Approved active runs may make a replay-safe bounded autonomous-continuation request using fresh server truth. Reconnect behavior cannot fabricate state, alter source authority or bypass the protected REVIEW/HUMAN_REQUIRED ceiling.

### W7-S4 — Safe Browser Tool Layer v1

The browser layer is a Project-scoped, non-destructive evidence capability admitted through the existing tool-authority registry.

V1 supports only bounded navigation, inspection, declarative assertion and viewport screenshot evidence against server-admitted HTTPS targets. Same-origin/off-origin policy, redirect validation, sensitive-observation redaction, action/time/output bounds and mandatory cleanup remain server-owned.

The browser capability exposes no arbitrary JavaScript/eval, generic fetch/request, credential/cookie/header manipulation, click/fill/upload/download, destructive API or unrestricted network authority. Browser evidence cannot override deterministic validation, accept source, transition a run, administer a provider/tool, merge, deploy or complete REVIEW.

### W7-S5 — Agentic observability, runtime economics and retention

S5 is a query-time evidence-aggregation layer over existing canonical server-owned data. It deliberately does not add a telemetry database, billing ledger, scheduler or new canonical retention/deletion store.

The accepted metric contract derives bounded values from Engineering Runs/attempts, run events, worker executions and accepted evaluation/delivery evidence. Metric truth is explicit:

- `OBSERVED` — directly derivable from complete authoritative evidence;
- `ESTIMATED` — bounded derivation where complete direct observation is unavailable;
- `UNKNOWN` — insufficient authoritative evidence; never silently converted to zero.

Provider usage/cost remain `UNKNOWN` until authoritative billable/provider evidence exists. This is preferable to inferred or synthetic cost truth.

Deterministic validation is the effective quality authority. Positive qualitative evaluation or a READY Preview cannot turn a deterministic failure into a successful quality result.

Run-event aggregation is replay-safe and Project/run-bound. Duplicate deterministic event identities do not double-count; conflicting replay content fails closed. Per-run event reads and Project history are bounded. When a bounded event window is incomplete relative to the authoritative latest sequence, S5 marks coverage incomplete and downgrades or withholds event-dependent claims rather than presenting partial evidence as complete observation.

S5 can populate the accepted S2 known-state economics presentation but cannot redefine S2 identity/control authority or require client-side metric inference.

Retention cleanup in the accepted S5 implementation is a deterministic query-time no-op. It may report the bounded retention policy but cannot delete or mutate Projects, Work Specifications, Engineering Runs, attempts/events, worker state, accepted source lineage, provider/delivery evidence or release records. Any future persisted derived-telemetry retention store would require a separate governed architecture/data lifecycle decision.

### Wave 7 cumulative integration boundary

Accepted Wave 7 S1–S5 are cumulative at `integration/wave7-productization` SHA `00a9e66e2f87a1f992d375b4217845b8f072e11d`.

This integration SHA is a development/integration identity, not a production identity. W7-S6 Integrated Product Proof remains the downstream acceptance/release boundary. A future Wave 7 production release must still satisfy exact-head protected gates, deployment prerequisites, exact release identity and post-cutover verification; no S1–S5 integration result by itself authorizes a `main` merge or production promotion.

## Model routing architecture

### Hosted baseline

With no admitted local-first configuration, runtime escalation remains exactly:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted production model identity and transport remain server-owned. Canonical hosted GPT-5.6 model IDs use the fixed OpenAI-compatible Vercel AI Gateway endpoint. A validated request-scoped Vercel runtime OIDC token is the automatic hosted-production credential authority. Process-environment `VERCEL_OIDC_TOKEN` is not runtime model-provider authority. There is no silent direct-OpenAI fallback.

Existing explicit `DSPY_API_BASE` / `DSPY_API_KEY` settings remain a deliberate whole-transport operator/development override. When that explicit override is present, local-first routing is disabled rather than combining two independently configurable transport paths.

### Local-first route policy

`P2-V0.19.8` introduces one optional server-owned local route that may precede the hosted chain only for a Parallax instance that can actually reach the configured operator-controlled inference endpoint.

The effective non-production/local-self-hosted order is therefore:

```text
optional admitted local route
      ↓ on provider failure or protected-validation rejection
Luna
      ↓
Terra
      ↓
Sol
```

A successful local result must pass the same existing protected validator used for hosted results. Local output does not receive a weaker acceptance path. A local provider failure records bounded sanitized attempt evidence and advances to the next admitted hosted route. A local protected-validation failure records `validation_failed` and advances without modifying the validator or acceptance policy.

The route is configuration-driven but not caller-controlled. Model identity, provider kind, endpoint and optional credential slot are resolved from server-owned configuration before model execution.

### Vercel production boundary

Vercel production is intentionally hosted-only under `P2-V0.19.8`.

When `VERCEL_ENV=production`, enabling local-first routing fails closed before any local endpoint request, whether the configured endpoint is loopback or remote HTTPS. This is an architectural boundary, not a temporary implementation limitation: a hosted Vercel function reaching a private/self-hosted inference service requires a separate architecture, network-security, identity, availability and deployment workstream.

The local-first capability therefore does not create an implicit tunnel, public local-model exposure, Vercel-to-LAN assumption or unrestricted network path.

### Provider/transport isolation

A local endpoint applies only to its exact admitted local model. It cannot rebind or redirect the canonical hosted GPT-5.6 routes.

Admitted local providers are constrained by provider/model-namespace compatibility. Endpoint configuration fails closed on malformed URLs, endpoint userinfo, query strings, fragments, malformed ports, unsupported provider/model combinations and non-loopback plaintext HTTP. Loopback plaintext HTTP is permitted only for appropriate local/self-hosted development use outside Vercel production; non-loopback endpoints require HTTPS.

Local model configuration cannot create generic network, source, tool or provider authority. It is only a model-transport binding consumed by the existing reasoning/implementation model seam.

### Credential isolation

Local endpoint credentials, when needed, may be resolved only through the dedicated server-owned `PARALLAX_LOCAL_MODEL_CREDENTIAL_*` environment-variable namespace.

A configured local credential slot cannot name arbitrary process environment variables and cannot reuse reserved hosted/provider authority such as AI Gateway, Vercel OIDC, database, GitHub/Vercel delivery or other application secrets.

Credentials are excluded from prompts, model outputs, attempt records, logs, persisted engineering evidence, client payloads, source packages and Sandbox environments.

### Diagnostics

Model-route evidence is deliberately bounded. A route attempt may expose only admitted model/provider identity, status, duration and sanitized exception class where applicable. Raw exception text, authorization values, endpoint credentials, prompts and generated content are not part of the routing evidence contract.

## Authority retained from v3.10

Wave 7 productization and local-first routing grant none of the following authority unless already explicitly provided by an existing protected server contract:

- Project creation/ownership or cross-Project access;
- Work Specification approval/amendment;
- Engineering Run stage transition beyond the existing protected server operations;
- accepted source-lineage creation or head advancement outside the existing single-writer boundary;
- filesystem/shell or arbitrary-command execution;
- unrestricted HTTP/network access;
- tool-capability creation or approval;
- provider spending/administration;
- GitHub repository/branch/PR merge authority;
- Vercel project/production promotion authority;
- approval, `REVIEW` completion or human-boundary bypass.

Canonical identity, source acceptance and execution remain controlled by the existing Project/spec/run/lineage contracts. Candidate model, benchmark, browser, projection and observability output is evidence, not authority.

## Wave 6 runtime architecture retained

The accepted Wave 6 production composition remains cumulative with local-first routing and the accepted Wave 7 development layers:

- S1 agent adapter/evidence admission binds exact Project/run/spec/acceptance/source identity;
- S2 chooses the smallest adequate admitted team and bounds coordination/reassignment;
- candidate work is non-canonical until protected integration;
- disposable candidate BUILD/TEST/VERIFY executes in deny-all Vercel Sandbox materializations with no application-secret environment;
- S3 independent evaluation cannot override deterministic failure;
- S4 routes only among already admissible strategies and cannot trade correctness/safety/privacy/governance for economics;
- S5 competition/synthesis cannot select failed or unvalidated candidates and synthesized candidates require fresh exact validation;
- one selected candidate reaches `ProtectedImplementationRuntime`;
- selected-candidate artifacts are private immutable replay evidence only;
- `ProtectedImplementationRuntime` and the source-lineage CAS remain the only canonical IMPLEMENT/source writer boundary;
- exact accepted lineage is required for authoritative BUILD/TEST/VERIFY and delivery;
- Preview remains the ordinary autonomous publication ceiling;
- operator REVIEW remains the autonomous authority ceiling.

Local-first model routing may be used by an eligible model-consuming seam outside Vercel production, but it cannot alter any of these authority boundaries. Wave 7 projection/browser/observability layers consume or present the existing authority/evidence plane and likewise cannot replace it.

## Persistence and deletion retained

Accepted Wave 7 S1–S5 and `P2-V0.19.8` add no new canonical authority store. S5 specifically adds no telemetry migration or billing ledger.

PostgreSQL/Supabase remains authoritative for application metadata, Projects, Work Specifications, Engineering Runs/attempts, durable worker executions, authorized users, source-lineage manifests/heads and activated observation data. Private immutable object storage remains authoritative for source objects and selected-candidate replay artifacts.

Logical workspace deletion remains a tombstone/visibility operation, not evidence purge. Protected Work Specifications, Engineering Runs, attempts/events, source lineage and immutable provider/evaluation evidence remain retained. Deleting a Project never deletes linked GitHub/Vercel resources.

## Execution and provider boundaries retained

Vercel Sandbox remains the isolated execution plane for protected accepted-lineage and disposable candidate validation. Registered commands only, deny-all networking by default, bounded resources and empty application-secret environment remain non-weakenable.

GitHub/Vercel delivery remains project-scoped and server-registered. Request-scoped Vercel OIDC and exact repository/connector/Preview target binding remain separate from model routing. A local model endpoint or credential cannot be interpreted as GitHub/Vercel delivery authority.

Provider actions and replay identities remain durable and bounded. Replaying an already accepted exact provider action resolves the accepted delivery record instead of duplicating mutation/publication.

The Wave 7 browser capability is separately constrained to admitted non-destructive browser evidence; it is not a substitute for the protected GitHub/Vercel provider or Sandbox execution planes.

## Production topology and release contract

The two long-lived application projects remain:

1. `parallax` — Expo/static web client;
2. `parallax-api` — FastAPI service.

`main` remains the production source branch. Path-aware build behavior may retain a previously verified component artifact when a change does not affect that component root.

A release is not deployment-verified merely because source is integrated. Promotion still requires applicable exact-head CI/evaluation, production prerequisite/preflight success, exact production deployment identity, health/readiness checks, runtime-error inspection and evidence-based state reconciliation.

For model-routing changes, production verification must additionally prove that the hosted-production path remains healthy and server-owned. Local/self-hosted execution cannot be truthfully claimed as Vercel-production behavior because Vercel production intentionally rejects local-first configuration.

Accepted Wave 7 S1–S5 are integration-only at this revision. Their green worker/Preview evidence demonstrates candidate validity; it is not production verification.

## Failure degradation additions

In addition to all v3.10 failure rules:

- local-first enabled in Vercel production → fail closed before local provider request;
- empty, duplicate, malformed or unsupported local route configuration → fail before model execution;
- local model identity colliding with the hosted chain → reject configuration;
- local provider/model namespace mismatch → reject configuration;
- non-loopback plaintext HTTP local endpoint → reject configuration;
- endpoint userinfo/query/fragment or malformed port → reject configuration;
- local credential slot outside `PARALLAX_LOCAL_MODEL_CREDENTIAL_*` → reject configuration;
- missing configured local credential → sanitized transport-configuration failure;
- local provider failure → bounded sanitized evidence then hosted fallback where policy permits;
- local protected-validation rejection → `validation_failed` then hosted fallback;
- hosted production request OIDC unavailable → fail hosted production model request; never substitute local credentials or process `VERCEL_OIDC_TOKEN`;
- browser target/action outside the admitted bounded S4 policy → deny without widening network/tool authority;
- cross-Project or cross-run observability evidence → fail closed;
- conflicting replayed event identity → fail closed;
- bounded event window incomplete → mark coverage incomplete and downgrade/withhold event-dependent S5 claims;
- provider usage/cost evidence absent → return `UNKNOWN`, not zero or synthetic estimate;
- S5 retention cleanup request → deterministic no-op under the accepted query-time-only retention contract.

## Security invariants

No provider secret, production root secret, Vercel execution credential or local-model credential is shipped to the client, browser evidence surface or Sandbox process.

User/model/agent content cannot redefine authentication, Project ownership, Work Specification approval, required acceptance criteria, accepted source lineage, worker ownership, deterministic validation, agent/team/evaluator/routing/competition policy, tool capabilities, executable commands, provider targets, hosted endpoint/credential admission, local route configuration, local credential slots, browser target/action admission, observability metric definitions/provenance rules, protected evaluation, run-event activation or deployment state.

The local-first route, Wave 7 browser tool and S5 observability surface add bounded evidence capabilities; they do not widen the canonical platform trust perimeter.

## Deployment and integration evidence for this architectural revision

Local-first production revision retained:

- accepted semantic worker `457541490aae196ee9e8cb65434f7b5570b829fc`;
- integration PR #345;
- integrated application source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- production API deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo` — READY;
- main Workstream Spec Validation #505 / run `33134841900` — PASS;
- main Parallax P2 CI #1159 / run `33134841915` — PASS;
- production `/health` and `/ready` — HTTP 200;
- exact-deployment `error`/`fatal` runtime scan — clean.

Wave 7 integration evidence through S5:

- W7-S4 PR #357 accepted worker `cda9e1e2c1de73ff20dbae8637fbdac63f810166`, Workstream #549, Bounded #789, P2 #1220, READY Preview `dpl_fpME2HH7x5jAQdL1haaPXLdhUJqK`, integrated as `e98526bccd8e62530098a7e59991d837b515be0c`;
- W7-S5 PR #360 accepted worker `26297f3fe3bbce4eca687c8a20b65d03b8476db9`, authentic DSPy run #182 / `33180827909`, Workstream #565 / `33184346124`, Bounded #804 / `33182504539`, release P2 #1237 / `33184346191`, READY Preview `dpl_E3iA7BbET4ZCt8TMFAjdJ1LMxrkb`, integrated as `00a9e66e2f87a1f992d375b4217845b8f072e11d`.

The Wave 7 evidence proves accepted cumulative development integration through S5. It does not prove a Wave 7 `main` merge or production deployment.