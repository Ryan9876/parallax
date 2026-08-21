# Parallax 2.0 Architecture

Version: 1.8
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by durable PostgreSQL persistence in hosted environments. Conversation remains the primary product surface. Reason, Code, work-specification drafting, protected evaluation, and release evidence are separate governed capabilities behind that surface.

```text
Expo / React Native client
  ├─ accessible conversation text
  ├─ response state machine
  ├─ React Native Skia optical material / beam effects
  ├─ reduced-graphics fallback
  ├─ compact work-specification surface
  ├─ Code run status surface
  ├─ same-origin /p2-api web gateway
  └─ SSE + JSON API client
          │
          ▼
FastAPI intelligence service
  ├─ signed browser-session boundary + bearer compatibility
  ├─ conversation service + durable product-policy spec identity
  ├─ work-specification service + revision/approval policy
  ├─ deterministic bounded Reason context composer
  ├─ DSPy scope program + protected scope policy
  ├─ DSPy Reason program + protected verifier
  ├─ DSPy work-specification drafter + protected structural validation
  ├─ Luna → Terra → Sol model routers
  ├─ durable Code engineering-run kernel
  └─ observable execution/failure traces
          │
          ├───────────────► protected evaluation spine
          │                  ├─ development suites
          │                  ├─ promotion suites
          │                  ├─ deterministic scorer
          │                  ├─ evidence artifacts
          │                  └─ baseline/challenger gate
          ▼
SQLite (development) / dedicated Supabase PostgreSQL (hosted)
```

## Core boundaries

### Client

The client owns interaction state and presentation. It does not own provider credentials, the production root access secret, durable conversation truth, work-specification approval authority, protected evaluation rules, or material-scope authority.

Assistant content is rendered as standard React Native `Text`. Skia is used for living material, optical beam, glint, and decorative motion. This preserves accessibility and allows a no-Skia degradation path.

The response reducer remains the source of truth for `IDLE`, `THINKING`, `RESPONDING`, `VERIFYING`, `COMPLETE`, `SPEC_AMENDMENT`, and `ERROR`. Motion and laser energy are derived from product state rather than independent animation state.

`SPEC_AMENDMENT` is a protected hand-off state, not a generic error. The client preserves the conversation and user turn, shows the server-provided hand-off, and stops substantive continuation against the prior approved objective.

For deployed web builds, protected API traffic is same-origin `/p2-api/*` traffic. Vercel rewrites that path to the configured API origin. Local web and native development may use the configured direct API origin. No provider or API root secret is embedded in the web bundle.

### Live response transport and optical typesetting

Reason responses use server-sent events. State events drive the response reducer and text chunks append to one growing assistant message.

The optical typesetter continuously chases the growing text target while the SSE stream is active; it does not wait for the full response and replay it. Fresh glyphs receive a short optical-energy tail, wrapped lines reset the active head geometry, and the product advances to `VERIFYING` only after the stream closes and the renderer catches up.

For `SPEC_AMENDMENT`, no substantive response chunks are emitted. Recoverable protected failures use sanitized SSE error events and observable trace metadata without candidate text or hidden reasoning.

### API

Routes call services/coordinators. Services call repositories and intelligence adapters. Provider SDK details do not leak into route contracts.

Operational probes are intentionally public and distinct:

- `/health` proves the FastAPI process can answer;
- `/ready` executes a database `select 1` and proves persistence is reachable.

All conversation, Reason, Code, work-specification, and session-status data routes remain behind the server-owned private-access boundary.

## Conversation and specification identities

### Product-policy specification identity

`Conversation.spec_id` is Parallax's durable product/policy specification identity. New conversations receive the configured `PARALLAX_ACTIVE_SPEC_ID`; existing conversations retain the stored identity they were created under. Product-release advancement therefore does not silently rewrite a resumed conversation's governing policy identity.

### User work specifications

User work specifications are a separate durable entity and must never reuse or reinterpret `Conversation.spec_id`.

Each `WorkSpecification` is linked to exactly one conversation and records:

- opaque work-specification ID;
- conversation ID;
- integer revision;
- status: `DRAFT`, `APPROVED`, or `SUPERSEDED`;
- title and objective;
- bounded constraints;
- bounded acceptance criteria;
- bounded risks;
- bounded open questions;
- draft confidence;
- drafting program/model identity when available;
- created/updated timestamps;
- optional approval timestamp.

The database enforces unique `(conversation_id, revision)` values and cascades work-specification deletion when its parent conversation is deleted.

### Work-specification lifecycle

Drafting is AI-assisted but approval is human-controlled.

```text
CONVERSATION WITH USER OBJECTIVE
   ↓
BOUNDED OBSERVABLE CONTEXT
   ↓
WORK-SPEC ROUTER (Luna → Terra → Sol)
   ↓
TYPED DSPy DRAFT
   ↓
PROTECTED STRUCTURAL VALIDATION
   ├─ all candidates fail ─► sanitized recoverable failure; persist nothing
   └─ valid candidate ─────► persist next DRAFT revision
                                   │
                                   ├─ newer draft supersedes older unapproved DRAFT
                                   └─ existing APPROVED revision remains approved
                                          until explicit operator approval

OPERATOR APPROVE
   ↓
selected DRAFT → APPROVED
prior APPROVED → SUPERSEDED
```

A model may create a candidate but may not approve it. Approval is an explicit protected server mutation. Approving an already approved revision is idempotent. Superseded revisions remain durable history even though the first client surface shows the latest revision.

The work-specification API contract is:

- `GET /v1/conversations/{conversation_id}/work-specifications/latest`
- `POST /v1/conversations/{conversation_id}/work-specifications/draft`
- `POST /v1/work-specifications/{specification_id}/approve`

The client presents this as one compact expandable strip rather than a requirements dashboard. Main Skia and reduced-graphics paths expose the same capture, inspect, refresh, and approve semantics.

## Reason architecture

### Deterministic Reason context

`intelligence/context.py` composes provider-independent runtime context from durable server state. It preserves conversation/spec identity, lifecycle status, mode, current user turn, a bounded chronological prior-message window, explicit role markers, and the authority rule that later explicit user corrections supersede conflicting older assistant assumptions.

Hard limits bound total characters, individual prior messages, current-turn length, and message count. Oldest eligible context is removed first. The active product-policy spec and current user turn are not silently discarded. Context digest, included-turn count, and truncation status are observable trace metadata.

### Scope authority

The client is not material-scope authority. The DSPy scope program proposes `CONTINUE`, `CLARIFY`, or `SPEC_AMENDMENT`, and protected server policy owns transition semantics. Low-confidence amendment proposals are conservatively converted to clarification. The developer/test override is available only when explicitly enabled and is trace-visible.

If all scope candidates fail provider execution or protected validation, no scope decision is fabricated.

### Reason program and verification

The typed Reason program receives objective, deterministic context, mode, durable product-policy spec identity, and the protected scope decision. User-visible output includes an answer plus bounded observable confidence, uncertainties, assumptions, and program identity.

Protected verification rejects malformed, secret-bearing, hidden-reasoning, or scope-incompatible output before completion. Invalid output may escalate through the normal model router.

```text
USER TURN (durably preserved)
   ↓
DETERMINISTIC CONTEXT
   ↓
SCOPE ROUTER → PROTECTED SCOPE POLICY
   ├─ CONTINUE ─────► REASON ROUTER ─► PROTECTED VERIFY ─► RESPOND
   ├─ CLARIFY ──────► REASON ROUTER ─► one focused question ─► RESPOND
   └─ SPEC_AMENDMENT► durable status + hand-off ─► STOP
```

## Observable trace contract

Runtime traces are evidence, not chain-of-thought. They may include response/conversation/spec identity, program versions, protected decisions, context digest/count/truncation, model-attempt status, verification outcome, and final product state.

Invalid candidate text, DSPy rationale, scratchpads, hidden chain-of-thought, provider credentials, database URLs, and environment values are excluded.

Work-specification failure paths follow the same rule: only sanitized failure information crosses the API boundary, and raw provider output/diagnostics are not persisted as work-specification content.

## Persistence

SQLAlchemy 2 provides SQLite development support and PostgreSQL through `DATABASE_URL`.

Hosted persistence uses the dedicated Parallax 2.0 Supabase PostgreSQL project. Vercel's ephemeral API functions connect through Supabase/Supavisor transaction pooling; SQLAlchemy uses provider-side pooling rather than maintaining long-lived application pools in preview/production.

Production schema evolution uses ordered SQL migrations under `services/api/migrations`. Production startup performs no implicit DDL. Development/tests may explicitly opt into metadata bootstrap.

The hosted schema includes durable conversations, messages, engineering runs/attempts, and work specifications. The work-specification table uses RLS and revokes direct `anon` and `authenticated` table privileges to match the existing server-owned data model.

## Private production access

Parallax production remains private and single-operator. `PARALLAX_ACCESS_TOKEN` is the root operator secret. Production requires high entropy and validates candidates using constant-time comparison. Bearer authentication remains supported for Swagger, automation, and non-browser clients.

The browser uses the bearer only to establish a short-lived signed session through `POST /v1/session`. The bearer is cleared from JavaScript state after exchange and is not stored in `localStorage` or `sessionStorage`.

Browser authorization is carried in a bounded HMAC-signed, `HttpOnly`, `Secure`, host-only, `SameSite=Lax` cookie. Cookie-authenticated protected requests additionally require `X-Parallax-Session: 1`. Missing, invalid, expired, or tampered authorization returns the same sanitized `401` contract.

Deployed browser traffic uses same-origin `/p2-api` so authentication does not depend on third-party-cookie behavior. Direct API CORS remains explicitly restricted.

## Model routing

Runtime escalation order is:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Scope, Reason, and work-specification drafting use typed program boundaries and protected validation. Escalation occurs on provider/program failure or protected validation failure. Attempt metadata is retained without candidate payloads.

## DSPy development and optimization

DSPy operates in two planes:

1. **Product runtime** — typed scope, Reason, and work-specification modules can evolve without changing protected policy or API contracts.
2. **Parallax development** — spec compilation/critique uses DSPy with protected metrics.

CI supports provider-backed development when approved credentials exist and a credential-free local Ollama compiler/critic path otherwise. The local path proves required DSPy execution but is not the final quality authority.

Optimizer-controlled code may not change the protected acceptance/evaluation functions used to promote a challenger.

## Code 2.0 execution kernel

Code mode owns a durable engineering run bound to its conversation and product-policy specification. Protected policy advances `SPECIFY → PLAN → IMPLEMENT → BUILD → TEST → VERIFY → REVIEW → COMPLETE`; pause, failure, amendment, cancellation, replay, and stale-revision conflict are explicit durable states/transitions.

The Code boundary includes append-only attempts, protected plan/implementation/execution/review validators, provider-neutral workspace artifact identity, deny-by-default typed execution contracts, deterministic recorded execution for CI, API orchestration, and an accessible client status surface.

BUILD, TEST, and VERIFY require successful execution evidence. IMPLEMENT cannot pass on prose alone. REVIEW cannot authorize merge/deployment merely from model output.

**v0.7.0 intentionally does not bind Code engineering runs to `WorkSpecification.id`.** That binding remains a later protected architecture step so the new user-work specification contract can stabilize independently.

A future live executor remains disabled by default and requires an explicit bounded workspace provider and command registry.

## Protected evaluation spine

Development and promotion benchmark suites are separate. Optimizers may consume development examples/feedback but not promotion expected answers or authority.

`services/api/parallax_api/evaluation/` owns deterministic protected scoring, safe benchmark/evidence loading, evidence construction, and baseline/challenger comparison. Critical protected regressions cannot be compensated by unrelated aggregate improvements.

Evaluation artifacts record observable identities, digests, per-case outcomes, category summaries, aggregate/protected pass state, and explicit no-chain-of-thought evidence. Candidate output is untrusted and secret/hidden-reasoning content is rejected.

Promotion remains an explicit release decision. Passing evaluation does not itself merge, deploy, alter protected thresholds, or prove production deployment.

## Deployment topology

Parallax has two authoritative Vercel projects from the same repository:

1. **Web — `parallax`**: root `apps/client`; Expo web export; static output `dist`.
2. **API — `parallax-api`**: root `services/api`; Vercel Python/FastAPI entrypoint through `api/index.py`.

Feature branches create previews in those same projects. Temporary/version/smoke projects are not release evidence.

The web project owns only public client configuration. The API project owns database/provider credentials, private access configuration, runtime model configuration, scope-override configuration, and direct-API CORS settings.

`main` is the production source branch. Release branches are validated through GitHub protected checks and Vercel preview evidence before merge. Provider `READY` status alone is insufficient for deployment verification.

### Deployment verification

Verification evidence must cover the material behavior changed by the release in addition to inherited health/security checks. The baseline evidence set includes:

- responsive web artifact and reduced-graphics behavior;
- Skia/CanvasKit initialization where available;
- API `/health` and database-backed `/ready`;
- sanitized unauthenticated `401` for protected routes;
- same-origin `/p2-api` reachability;
- durable conversation/spec identity;
- Reason SSE/optical behavior and amendment/failure paths;
- durable Code state where changed;
- work-specification table/migration security and route exposure where changed;
- authenticated work-specification draft/approval round trip when claiming the work-specification release fully deployment-verified;
- exact Git/Vercel deployment identities without exposing secrets.

## Web Skia

React Native Skia uses CanvasKit/WASM on web. `apps/client/scripts/setup-skia-web.mjs` copies the matching `canvaskit.wasm` into the public directory. Skia initialization is deferred before the application root is registered.

The browser acceptance gate verifies responsive layout at 390×844, 768×1024, and 1440×900 and deliberately removes CanvasKit in a separate run to prove reduced-graphics functional parity. v0.7.0 extends that browser contract to work-specification capture, expansion, and explicit approval.

## Failure degradation

- Skia unavailable: use the static reduced-graphics path; conversation and work-specification semantics remain functional.
- Browser session invalid/expired: return sanitized `401`, preserve durable data, and return to private access without retaining the root credential.
- Same-origin proxy unavailable: show recoverable offline/private-session UI; never embed or persist the root secret.
- Context cannot fit protected bounds: preserve the user turn and return a sanitized recoverable context error.
- Scope exhaustion: preserve the turn and record no fabricated decision.
- Reason protected-invalid candidate: escalate Luna → Terra → Sol.
- Reason exhaustion: preserve the turn and return a sanitized recoverable failure.
- Work-spec drafting exhaustion/validation failure: persist no fake revision and return sanitized failure.
- Database failure: `/ready` returns sanitized failure and deployment verification is blocked.
- Development provider credentials unavailable: use the local DSPy compiler/critic path without claiming provider-backed optimization.
- Protected evaluation regression: block promotion and retain machine-readable evidence.
- Preview regression: keep production on the last known-good deployment.

## Security

No model/provider secret or production root access secret is shipped to the client. Browser sessions are bounded and signed, and deployed web access remains same-origin through `/p2-api`.

Conversation content and generated work-specification fields are untrusted model inputs/outputs. They cannot redefine scope policy, authentication, approval authority, evaluation rules, or release state. Only bounded observable structured work-specification fields are persisted; raw provider diagnostics and hidden reasoning are excluded.

Hosted infrastructure remains isolated from unrelated application databases. The work-specification table follows the same RLS/revoked-client-role model as existing durable application data.

The protected evaluation subsystem is a trust boundary: optimizer code cannot obtain writable promotion authority, evidence artifacts may not contain secrets or hidden reasoning, and release claims must remain traceable to versioned evidence.