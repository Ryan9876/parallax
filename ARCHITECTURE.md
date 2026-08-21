# Parallax 2.0 Architecture

Version: 1.9
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by durable PostgreSQL persistence in hosted environments. Conversation remains the primary product surface. Reason, Code, user Work Specifications, protected evaluation, and release evidence are separate governed capabilities behind that surface.

```text
Expo / React Native client
  ├─ accessible conversation text
  ├─ response state machine
  ├─ React Native Skia optical material / beam effects
  ├─ reduced-graphics fallback
  ├─ compact Work Specification surface
  ├─ bound Code run status surface
  ├─ same-origin /p2-api web gateway
  └─ SSE + JSON API client
          │
          ▼
FastAPI intelligence service
  ├─ signed browser-session boundary + bearer compatibility
  ├─ durable conversation + product-policy spec identity
  ├─ Work Specification revision/approval service
  ├─ approved-spec Code activation policy
  ├─ immutable EngineeringRun ↔ WorkSpecification binding
  ├─ server-owned acceptance map
  ├─ deterministic bounded Reason context composer
  ├─ DSPy scope / Reason / Work Specification programs
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

The client owns interaction state and presentation. It does not own provider credentials, the production root access secret, durable conversation truth, Work Specification approval authority, required acceptance criteria, protected evaluation rules, material-scope authority, or execution-release authority.

Assistant content is rendered as standard React Native `Text`. Skia is used for living material, optical beam, glint, and decorative motion. The no-Skia reduced-graphics path preserves equivalent semantic state and capability.

The response reducer remains authoritative for `IDLE`, `THINKING`, `RESPONDING`, `VERIFYING`, `COMPLETE`, `SPEC_AMENDMENT`, and `ERROR`. Motion and optical energy derive from product state rather than independent animation state.

Deployed web protected API traffic is same-origin `/p2-api/*`, rewritten by Vercel to the configured API origin. No provider secret or API root access secret is embedded in the browser bundle.

### API

Routes call services/coordinators; services call repositories and intelligence adapters. Provider SDK detail does not leak into route contracts.

Operational probes remain deliberately public:

- `/health` proves the FastAPI process can answer;
- `/ready` executes a database query and proves persistence is reachable.

Conversation, Reason, Code, Work Specification, and session-status routes remain behind the private server authentication boundary.

## Specification identities

Parallax maintains two distinct specification identities.

### Product-policy specification

`Conversation.spec_id` is the durable Parallax product/policy specification identity. New conversations receive the configured active spec; existing conversations retain the identity they were created under. Product releases do not silently rewrite resumed conversations.

### User Work Specification

A `WorkSpecification` is the operator-controlled implementation contract for one conversation objective. It records:

- opaque ID and conversation ID;
- integer revision;
- lifecycle state `DRAFT`, `APPROVED`, or `SUPERSEDED`;
- title/objective;
- bounded constraints;
- bounded acceptance criteria;
- bounded risks/open questions;
- confidence and drafting program/model identity;
- created/updated/approved timestamps.

The database enforces unique `(conversation_id, revision)` values. Drafting may be AI-assisted; approval is an explicit protected operator mutation. A model cannot approve its own output.

```text
USER OBJECTIVE
   ↓
BOUNDED CONVERSATION CONTEXT
   ↓
WORK-SPEC ROUTER (Luna → Terra → Sol)
   ↓
TYPED DRAFT + PROTECTED VALIDATION
   ↓
DRAFT revision
   ↓ explicit operator approval
APPROVED revision
   └─ prior approved revision → SUPERSEDED
```

Work Specification routes include latest, latest-approved, draft, and approve operations. The client exposes them as compact conversation-native controls rather than a project-management dashboard.

## Approved-Spec Code execution binding

v0.8.0 makes the approved user Work Specification the authoritative contract for every new Code engineering run.

Each new `EngineeringRun` persists:

- product-policy `spec_id`;
- `work_specification_id`;
- `work_specification_revision`;
- `work_specification_digest`;
- normal durable run state/revision/workspace metadata.

The Work Specification digest is computed server-side from bounded, product-visible contract fields: specification ID, revision, title, objective, constraints, acceptance criteria, risks, and open questions. Approval timestamp/status bookkeeping is excluded so approval does not change content identity.

The binding columns are nullable only for historical pre-v0.8 runs. New v0.8 runs cannot be created as authoritative execution evidence without an approved Work Specification binding.

### Approval gate

Code activation requires:

- a Code conversation;
- conversation not in `SPEC_AMENDMENT`;
- an approved Work Specification belonging to that conversation;
- positive persisted revision;
- product-policy `spec_id` consistent with the durable conversation.

A `DRAFT`, `SUPERSEDED`, missing, or foreign-conversation Work Specification cannot activate Code.

### Immutable target

Once a run is created, its Work Specification ID/revision/digest are immutable through stage advance, pause, resume, refresh, and subsequent Work Specification lifecycle changes.

A newer draft does not retarget a run. A newly approved revision creates or reuses only a run already bound to that exact newer revision.

This prevents execution drift from conversation changes after work has begun.

### Server-owned acceptance map

The server derives stable acceptance IDs from the bound Work Specification in list order:

```text
criterion 1 → AC-01
criterion 2 → AC-02
criterion 3 → AC-03
...
```

Clients, models, and tools may submit evidence *against* these IDs, but they do not define the required set.

The engineering-run read contract exposes the binding identity and acceptance map for operator visibility.

### Protected Code lifecycle

Protected policy advances:

`SPECIFY → PLAN → IMPLEMENT → BUILD → TEST → VERIFY → REVIEW → COMPLETE`

The product activation path is `POST /v1/engineering-runs/activate`.

For a newly activated run, the server records protected `SPECIFY` binding evidence and advances to `PLAN`. Activation does not grant unrestricted execution authority.

Protected coverage rules:

- `PLAN` must exactly cover the server-owned acceptance set;
- `IMPLEMENT` still requires real bounded artifact/workspace evidence rather than prose;
- `BUILD` must target the full acceptance set and provide successful protected execution evidence;
- `TEST` must exercise the full acceptance set with successful protected test evidence;
- `VERIFY` must verify the full acceptance set with successful protected verification evidence;
- `REVIEW` must verify the full set, recommend `PASS`, and match independently persisted implementation workspace identity.

Missing, duplicated, extra, or client-redefined acceptance IDs fail the protected gate.

Activation is idempotent for the same eligible conversation + approved Work Specification. It may reuse a compatible nonterminal exact-bound run but cannot retarget an older run.

## Execution authority boundary

v0.8.0 strengthens the execution contract but deliberately does **not** enable:

- unrestricted shell access;
- arbitrary command execution;
- autonomous Git commit/push/merge;
- autonomous Vercel promotion;
- autonomous production deployment;
- model self-approval of Work Specifications.

The current execution layer remains deny-by-default and evidence-oriented. A future live executor requires an explicit bounded workspace provider, command registry, trust policy, rollback model, and release authority contract.

## Reason architecture

Reason uses provider-independent bounded context assembled from durable server state. Later explicit user corrections supersede conflicting older assistant assumptions. Context limits are deterministic and preserve the current user turn plus governing product-policy identity.

The scope program proposes `CONTINUE`, `CLARIFY`, or `SPEC_AMENDMENT`; protected server policy owns the transition. Low-confidence material-scope changes are conservatively converted to clarification rather than silently continuing.

Typed Reason output is protected before completion. Invalid, secret-bearing, hidden-reasoning, or scope-incompatible candidates may escalate Luna → Terra → Sol.

```text
USER TURN
   ↓
DETERMINISTIC CONTEXT
   ↓
SCOPE ROUTER + PROTECTED POLICY
   ├─ CONTINUE ─────► REASON ROUTER ─► PROTECTED VERIFY ─► RESPOND
   ├─ CLARIFY ──────► one focused question
   └─ SPEC_AMENDMENT► durable hand-off ─► STOP
```

## Live response transport and optical rendering

Reason responses use server-sent events. State events drive the reducer and text chunks append to one growing assistant message.

The optical typesetter follows the live text target; it does not wait for the whole response and replay it. Fresh glyphs receive a short optical energy tail before cooling to selectable narrative text.

`SPEC_AMENDMENT` emits no substantive answer chunks. Protected failure paths expose sanitized user-visible recovery information and observable metadata without hidden reasoning or candidate payloads.

## Persistence

SQLAlchemy 2 provides SQLite development support and PostgreSQL hosted support through `DATABASE_URL`.

Production uses the dedicated Parallax 2.0 Supabase PostgreSQL project through Supavisor transaction pooling. Vercel functions do not depend on long-lived application-side pools.

Production schema evolution is migration-driven under `services/api/migrations`; production startup performs no implicit DDL.

Current hosted schema includes:

- conversations;
- messages;
- work specifications;
- engineering runs;
- engineering attempts.

The v0.8 additive migration adds nullable historical-compatibility binding columns to `engineering_runs`, a restrictive foreign key to `work_specifications`, and an index on the binding ID.

RLS is enabled on server-owned tables and direct client-role access is not the application data path. The FastAPI service remains the authoritative data boundary.

## Private production access

Production is private and single-operator. `PARALLAX_ACCESS_TOKEN` is the root operator secret and is validated server-side with constant-time comparison.

Bearer authentication remains available for Swagger/automation/non-browser clients. Browser clients use bearer only to establish a short-lived signed session through `POST /v1/session`; the bearer is then cleared from JavaScript state and is never persisted in `localStorage` or `sessionStorage`.

Browser authorization uses a bounded HMAC-signed `HttpOnly`, `Secure`, host-only, `SameSite=Lax` cookie. Cookie-authenticated protected requests also require `X-Parallax-Session: 1`.

Same-origin `/p2-api` traffic avoids third-party-cookie dependence.

## Model routing and DSPy

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Scope, Reason, and Work Specification drafting use typed boundaries and protected validation.

DSPy operates in two planes:

1. product runtime typed modules;
2. Parallax development SpecCritic/SpecCompiler optimization and validation.

CI may use provider-backed development when approved credentials exist and a local Ollama path otherwise. Optimizer-controlled code cannot change protected promotion/evaluation authority.

## Protected evaluation spine

Development and promotion benchmark suites are separate. Optimizers may consume development examples but not promotion expected answers or protected authority.

Evaluation evidence records observable IDs, digests, outcomes, summaries, protected pass state, and explicit no-chain-of-thought evidence. Candidate output is untrusted and secret/hidden-reasoning content is rejected.

Passing evaluation does not itself authorize merge or deployment.

## Deployment topology

Two authoritative Vercel projects deploy from the same repository:

1. Web `parallax` — root `apps/client`, Expo static export to `dist`.
2. API `parallax-api` — root `services/api`, FastAPI via `api/index.py`.

`main` is the production source branch. Feature branches create previews. Path-aware ignore commands prevent redundant project builds when a commit does not touch that project's root.

Release promotion requires exact-head CI, relevant preview evidence, migration readiness when schema changes, production Vercel readiness, live health/readiness, same-origin protected-route verification, and evidence-based status recording.

## Web Skia

React Native Skia uses CanvasKit/WASM on web. The build copies the matching `canvaskit.wasm` into the public directory before export.

Browser acceptance covers mobile, tablet, desktop, animated Skia behavior, optical response inscription, and a deliberate CanvasKit-unavailable reduced-graphics run. v0.8 additionally exercises the approved Work Specification → Code binding lifecycle and reduced-graphics bound-run parity.

## Failure degradation

- Skia unavailable: preserve content/capability in the static reduced-graphics path.
- Browser session invalid/expired: sanitized 401 and return to private access without retaining root credentials.
- Same-origin proxy unavailable: recoverable offline/private-session UI; never embed the root secret.
- Context cannot fit protected bounds: preserve user turn and return a sanitized context failure.
- Scope exhaustion: preserve turn and fabricate no decision.
- Reason protected-invalid candidate: escalate provider/model route.
- Work Specification drafting failure: persist no fake revision.
- No approved Work Specification: block Code activation rather than improvising an execution target.
- Binding mismatch/digest conflict: block protected execution and preserve evidence.
- Database failure: `/ready` fails and deployment verification is blocked.
- Protected evaluation regression: block promotion.
- Preview regression: keep production on the last known-good deployment.

## Security

No provider secret or production root access secret is shipped to the client. Conversation and Work Specification content are untrusted model/user data and cannot redefine authentication, approval authority, required acceptance criteria, protected evaluation, execution policy, or deployment state.

The approved Work Specification binding is a trust boundary: the server owns its digest and acceptance map, while the client owns only interaction intent. Engineering evidence may demonstrate satisfaction of the contract but cannot redefine the contract.

Release claims remain traceable to versioned Git, migration, CI, and Vercel evidence.
