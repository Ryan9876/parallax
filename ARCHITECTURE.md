# Parallax 2.0 Architecture

Version: 3.10
Status: Authoritative

## Version relationship

Architecture v3.10 is a bounded architectural update to v3.9, not a platform rewrite. The complete v3.9 architecture at repository commit `15eba922db816b90256f4a4ed40624bb5604b53f` is incorporated by reference. Every v3.9 durable contract that is not explicitly changed below remains authoritative, including canonical Project/Work Specification/Engineering Run authority, immutable accepted source lineage, single-writer IMPLEMENT mutation, durable worker recovery, deny-all Sandbox validation, Wave 6 agentic orchestration/evaluation/routing/competition boundaries, project-scoped tool/provider authority, logical workspace deletion/retention, protected evaluation, Preview/REVIEW ceilings and governed release evidence.

This version records one durable change: accepted `P2-V0.19.8` local-first model routing. It also reconciles the architectural status of Wave 6 from “integrated/undeployed” to the already verified production state recorded in `CURRENT-STATE.md`.

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

## Authority retained from v3.9

Local-first routing changes model selection/transport only. It grants none of the following authority:

- Project creation/ownership or cross-Project access;
- Work Specification approval/amendment;
- Engineering Run stage transition;
- accepted source-lineage creation or head advancement;
- filesystem/shell or arbitrary-command execution;
- unrestricted HTTP/network access;
- tool-capability creation or approval;
- provider spending/administration;
- GitHub repository/branch/PR merge authority;
- Vercel project/production promotion authority;
- approval, `REVIEW` completion or human-boundary bypass.

Canonical identity, source acceptance and execution remain controlled by the existing Project/spec/run/lineage contracts. Candidate model output is evidence, not authority.

## Wave 6 runtime architecture retained

The accepted Wave 6 production composition remains cumulative with local-first routing:

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

Local-first model routing may be used by an eligible model-consuming seam outside Vercel production, but it cannot alter any of these authority boundaries.

## Persistence and deletion retained

`P2-V0.19.8` adds no database schema and no new durable authority store.

PostgreSQL/Supabase remains authoritative for application metadata, Projects, Work Specifications, Engineering Runs/attempts, durable worker executions, authorized users, source-lineage manifests/heads and activated observation data. Private immutable object storage remains authoritative for source objects and selected-candidate replay artifacts.

Logical workspace deletion remains a tombstone/visibility operation, not evidence purge. Protected Work Specifications, Engineering Runs, attempts/events, source lineage and immutable provider/evaluation evidence remain retained. Deleting a Project never deletes linked GitHub/Vercel resources.

## Execution and provider boundaries retained

Vercel Sandbox remains the isolated execution plane for protected accepted-lineage and disposable candidate validation. Registered commands only, deny-all networking by default, bounded resources and empty application-secret environment remain non-weakenable.

GitHub/Vercel delivery remains project-scoped and server-registered. Request-scoped Vercel OIDC and exact repository/connector/Preview target binding remain separate from model routing. A local model endpoint or credential cannot be interpreted as GitHub/Vercel delivery authority.

Provider actions and replay identities remain durable and bounded. Replaying an already accepted exact provider action resolves the accepted delivery record instead of duplicating mutation/publication.

## Production topology and release contract

The two long-lived application projects remain:

1. `parallax` — Expo/static web client;
2. `parallax-api` — FastAPI service.

`main` remains the production source branch. Path-aware build behavior may retain a previously verified component artifact when a change does not affect that component root.

A release is not deployment-verified merely because source is integrated. Promotion still requires applicable exact-head CI/evaluation, production prerequisite/preflight success, exact production deployment identity, health/readiness checks, runtime-error inspection and evidence-based state reconciliation.

For model-routing changes, production verification must additionally prove that the hosted-production path remains healthy and server-owned. Local/self-hosted execution cannot be truthfully claimed as Vercel-production behavior because Vercel production intentionally rejects local-first configuration.

## Failure degradation additions

In addition to all v3.9 failure rules:

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
- hosted production request OIDC unavailable → fail hosted production model request; never substitute local credentials or process `VERCEL_OIDC_TOKEN`.

## Security invariants

No provider secret, production root secret, Vercel execution credential or local-model credential is shipped to the client or Sandbox process.

User/model/agent content cannot redefine authentication, Project ownership, Work Specification approval, required acceptance criteria, accepted source lineage, worker ownership, deterministic validation, agent/team/evaluator/routing/competition policy, tool capabilities, executable commands, provider targets, hosted endpoint/credential admission, local route configuration, local credential slots, protected evaluation, run-event activation or deployment state.

The local-first route adds a bounded model-transport choice; it does not widen the platform trust perimeter.

## Deployment evidence for this architectural revision

Accepted semantic worker: `457541490aae196ee9e8cb65434f7b5570b829fc`.  
Integration PR: #345.  
Integrated application source: `35113209d9ad43585a6cc5ba167774ab8d13e03c`.  
Production API deployment: `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo` — READY.  
Main Workstream Spec Validation #505 / run `33134841900` — PASS.  
Main Parallax P2 CI #1159 / run `33134841915` — PASS.  
Production `/health` — HTTP 200.  
Production `/ready` — HTTP 200 with database/providers healthy and one registered provider target.  
Exact-deployment `error`/`fatal` runtime scan — clean.

The production evidence proves the accepted code is deployed without degrading the hosted-production path. Local/self-hosted route behavior is validated by the exact-head protected test/evaluation suite; it is not exercised through Vercel production because the architecture intentionally forbids that configuration.
