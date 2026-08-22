# Parallax 2.0 Architecture

Version: 2.1
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by durable PostgreSQL persistence in hosted environments. Conversation remains the primary product surface. Reason, Code, user Work Specifications, identity/access control, protected evaluation, bounded execution, and release evidence remain separate governed capabilities behind that surface.

```text
Expo / React Native client
  ├─ accessible conversation text
  ├─ response state machine
  ├─ React Native Skia optical material / beam effects
  ├─ reduced-graphics fallback
  ├─ compact Work Specification surface
  ├─ bound Code run + bounded-autonomy status surface
  ├─ Google PKCE sign-in gate + owner access panel
  ├─ same-origin /p2-api web gateway
  └─ SSE + JSON API client
          │
          ▼
FastAPI intelligence service
  ├─ Google identity verification + authorized-user allowlist
  ├─ signed browser-session boundary + bearer break-glass compatibility
  ├─ durable conversation + product-policy spec identity
  ├─ Work Specification revision/approval service
  ├─ approved-spec Code activation policy
  ├─ immutable EngineeringRun ↔ WorkSpecification binding
  ├─ server-owned acceptance map
  ├─ deterministic bounded Reason context composer
  ├─ DSPy scope / Reason / Work Specification programs
  ├─ Luna → Terra → Sol model routers
  ├─ durable Code engineering-run kernel
  ├─ bounded autonomy coordinator
  ├─ server-owned protected command registry
  └─ observable execution/failure traces
          │
          ├───────────────► Vercel Sandbox execution plane
          │                  ├─ deployment-scoped Vercel identity
          │                  ├─ ephemeral Git-initialized workspace
          │                  ├─ deny-all network policy
          │                  ├─ empty application-secret environment
          │                  └─ bounded registered process execution
          │
          ├───────────────► protected evaluation spine
          │                  ├─ development suites
          │                  ├─ promotion suites
          │                  ├─ deterministic scorer
          │                  ├─ evidence artifacts
          │                  └─ baseline/challenger gate
          ▼
SQLite (development) / dedicated Supabase PostgreSQL + Auth (hosted)
```

## Core boundaries

### Client

The client owns interaction state and presentation. It does not own provider credentials, the production root access secret, durable conversation truth, durable authorization truth, Work Specification approval authority, required acceptance criteria, protected evaluation rules, executable command definitions, material-scope authority, or release authority.

Assistant content is rendered as standard React Native `Text`. Skia is used for living material, optical beam, glint, and decorative motion. The no-Skia reduced-graphics path preserves equivalent semantic state and capability.

The response reducer remains authoritative for `IDLE`, `THINKING`, `RESPONDING`, `VERIFYING`, `COMPLETE`, `SPEC_AMENDMENT`, and `ERROR`. Motion and optical energy derive from product state rather than independent animation state.

Deployed web protected API traffic is same-origin `/p2-api/*`, rewritten by Vercel to the configured API origin. No provider secret, Vercel execution credential, or API root access secret is embedded in the browser bundle.

Google sign-in uses a browser-owned PKCE verifier held only in `sessionStorage` for the OAuth redirect round trip. A transient Supabase access token proves identity to the Parallax API and is not retained as the Parallax session credential.

The Code run surface may request a bounded autonomous cycle and show its observable stop reason. It cannot submit executable shell text, redefine acceptance coverage, or elevate the execution authority granted by the server.

### API

Routes call services/coordinators; services call repositories and intelligence/execution adapters. Provider SDK detail does not leak into route contracts.

Operational probes remain deliberately public:

- `/health` proves the FastAPI process can answer;
- `/ready` executes a database query and proves persistence is reachable.

Conversation, Reason, Code, Work Specification, access-management, session-status, and bounded-autonomy routes remain behind the private server authentication boundary.

The bounded-autonomy route is orchestration intent, not a shell endpoint. It accepts run identity, an idempotency operation key, and expected run revision; executable command text is never an API input.

## Identity and access architecture

Google/Supabase proves interactive identity. Parallax decides application authorization through the server-owned `authorized_users` allowlist.

Each allowlist record carries an opaque Parallax user ID, normalized email, optional bound Google/Supabase auth user ID, display metadata, `owner` or `member` role, `active` or `revoked` status, and lifecycle timestamps. First successful Google sign-in binds an enrolled email to the verified auth user ID. Subsequent access requires an active row and matching bound identity.

RLS is enabled and direct `anon` / `authenticated` table privileges are revoked; FastAPI remains the application authorization boundary.

`member` authorizes normal product use. `owner` additionally authorizes access-management mutations. Protected requests re-check current allowlist state, so revocation overrides an otherwise structurally valid signed session.

`PARALLAX_ACCESS_TOKEN` remains a server-only break-glass and explicit automation credential. It is not the normal hosted browser login path and is never exposed to the bounded sandbox.

## Specification identities

Parallax maintains two distinct specification identities.

### Product-policy specification

`Conversation.spec_id` is the durable Parallax product/policy specification identity. New conversations receive the configured active spec; resumed conversations retain the identity under which they were created.

### User Work Specification

A `WorkSpecification` is the operator-controlled implementation contract for one conversation objective. It contains a revision, lifecycle state (`DRAFT`, `APPROVED`, `SUPERSEDED`), objective, constraints, acceptance criteria, risks/open questions, confidence, drafting-program/model identity, and lifecycle timestamps.

Drafting may be AI-assisted; approval is an explicit protected operator mutation. A model cannot approve its own output.

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

The client exposes Work Specification lifecycle controls as compact conversation-native controls rather than a project-management dashboard.

## Approved-Spec Code execution binding

Every new authoritative Code engineering run is bound to one approved Work Specification revision. Each run persists product-policy `spec_id`, Work Specification ID/revision/digest, run state/revision, workspace identity, attempts, and observable evidence.

The server computes the Work Specification digest from bounded product-visible contract fields. A newer draft or later approval never retargets an in-flight run.

Code activation requires a Code conversation, no active `SPEC_AMENDMENT`, an approved Work Specification owned by that conversation, a positive persisted revision, and product-policy spec consistency.

### Server-owned acceptance map

The server derives stable acceptance IDs from the bound Work Specification in list order:

```text
criterion 1 → AC-01
criterion 2 → AC-02
criterion 3 → AC-03
...
```

Clients, models, and tools may submit evidence against these IDs but cannot define the required set.

### Protected Code lifecycle

Protected policy advances:

`SPECIFY → PLAN → IMPLEMENT → BUILD → TEST → VERIFY → REVIEW → COMPLETE`

Activation records protected `SPECIFY` binding evidence and advances to `PLAN`. Protected validators require exact server-owned acceptance coverage and real evidence:

- `PLAN`: exact acceptance coverage and protected work/check map;
- `IMPLEMENT`: real bounded artifact/workspace evidence rather than prose;
- `BUILD`: full target coverage and successful protected execution evidence;
- `TEST`: full verified coverage and successful protected test evidence;
- `VERIFY`: full verified coverage and successful protected verification evidence;
- `REVIEW`: full coverage, `PASS` recommendation, and independent agreement with persisted implementation workspace identity.

Missing, duplicated, extra, or client-redefined acceptance IDs fail the protected gate. Stage transitions continue to use optimistic revisions and idempotent operation records.

## Bounded autonomy execution plane

v0.13.0 introduces live isolated execution without granting general-purpose agent or release authority.

### Autonomy coordinator

A single operator request can advance only stages explicitly authorized by the current product policy. The coordinator re-reads the durable run before each step, enforces the caller's expected revision, and passes evidence through the existing protected Engineering Run validators rather than bypassing them.

At `PLAN`, the coordinator first performs an isolated executor preflight. If the execution provider is unavailable, the cycle stops with `EXECUTOR_UNAVAILABLE` and does not mutate PLAN state or revision. A successful preflight permits deterministic plan construction from the immutable acceptance map and advances to `IMPLEMENT`.

At `IMPLEMENT`, the pilot stops with `IMPLEMENTATION_REQUIRED`; it cannot fabricate source changes or implementation evidence.

At `BUILD`, `TEST`, and `VERIFY`, the coordinator selects a stage-specific command from server code, executes it through the bounded executor, maps successful evidence to the exact acceptance IDs, and advances only if the protected validator accepts the result.

At `REVIEW`, the pilot stops with `REVIEW_REQUIRED`. `PAUSED`, `FAILED`, `COMPLETE`, `CANCELLED`, and `SPEC_AMENDMENT` also stop without silent state mutation.

Command failure, timeout, provider unavailability, stale revision, or protected-validation failure cannot be recorded as a passing stage or cause a skipped transition.

### Protected command registry

Executable policy is code, not model output or API input. The initial registry contains only repository-specific structured command/argument arrays for:

- BUILD: Python compilation of the API package and Parallax scripts;
- TEST: protected Code/execution test subset;
- VERIFY: protected Code boundary/kernel verification subset.

No command is assembled by concatenating user/model strings. The registry supplies no application environment names and accepts no working-directory escape from the caller.

### Vercel Sandbox executor

The production-capable executor runs outside the FastAPI host using Vercel Sandbox. It uses deployment-scoped Vercel identity and project context available to the server runtime to create a short-lived sandbox. Repository-backed stages initialize the approved Git repository/revision before the process is run.

Every pilot sandbox is:

- non-persistent;
- bounded by a stage timeout plus small session margin;
- configured with deny-all network policy;
- created with an empty application environment;
- destroyed after use;
- invoked with a structured executable + argument array rather than a shell string.

Application secrets, the Parallax root bearer, provider API keys, and Vercel execution credentials are not forwarded into the sandbox process or persisted as run evidence.

The executor records only bounded observable evidence: tool identity, invocation digest, exit code, duration, stdout/stderr digests, bounded excerpts, timeout state, redaction state, executor/network policy identity, and protected acceptance coverage where required. Provider errors are sanitized and become non-success evidence rather than fabricated success.

### Authority boundary

Bounded autonomy does **not** authorize:

- arbitrary shell access or model-supplied commands;
- autonomous source-code editing or patch application;
- Work Specification self-approval/amendment;
- autonomous Git commit, push, merge, or history rewrite;
- autonomous Vercel promotion or production deployment;
- unsupported deployment-state claims.

Human/release authority remains outside the executor interface by design.

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

Reason responses use server-sent events. State events drive the reducer and text chunks append to one growing assistant message. The optical typesetter follows the live text target; fresh glyphs receive a short optical energy tail before cooling to selectable narrative text.

`SPEC_AMENDMENT` emits no substantive answer chunks. Protected failure paths expose sanitized user-visible recovery information and observable metadata without hidden reasoning or candidate payloads.

## Persistence

SQLAlchemy 2 provides SQLite development support and PostgreSQL hosted support through `DATABASE_URL`.

Production uses the dedicated Parallax 2.0 Supabase PostgreSQL project through Supavisor transaction pooling. The same Supabase project supplies Google OAuth brokering, while FastAPI remains authoritative for application authorization and data access.

Production schema evolution is migration-driven under `services/api/migrations`; production startup performs no implicit DDL.

Current hosted schema includes conversations, messages, work specifications, engineering runs, engineering attempts, and authorized users. Historical pre-v0.8 run-binding columns remain nullable for compatibility. RLS remains enabled on server-owned tables and direct client-role access is not the application data path.

v0.13.0 requires no new durable database table or schema migration; bounded execution evidence is recorded through the existing Engineering Run / attempt evidence model.

## Model routing and DSPy

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Scope, Reason, and Work Specification drafting use typed boundaries and protected validation. DSPy operates in runtime typed modules and in development SpecCritic/SpecCompiler optimization/validation. Optimizer-controlled code cannot change protected promotion/evaluation or execution authority.

## Protected evaluation spine

Development and promotion benchmark suites are separate. Optimizers may consume development examples but not promotion expected answers or protected authority.

Evaluation evidence records observable IDs, digests, outcomes, summaries, protected pass state, and explicit no-chain-of-thought evidence. Candidate output is untrusted and secret/hidden-reasoning content is rejected.

Passing evaluation does not itself authorize merge or deployment.

## Deployment topology

Two authoritative Vercel projects deploy from the same repository:

1. Web `parallax` — root `apps/client`, Expo static export to `dist`.
2. API `parallax-api` — root `services/api`, FastAPI via `api/index.py`.

`main` is the production source branch. Feature branches create previews. Path-aware ignore commands prevent redundant builds when a commit does not affect that project's root.

The bounded execution plane is runtime infrastructure used by the API; it is not a third Parallax application deployment. The API's Vercel runtime identity scopes Sandbox creation, while the sandbox itself remains ephemeral and isolated from the API host.

Release promotion requires exact-head CI, relevant preview evidence, migration readiness when schema changes, production Vercel readiness, live health/readiness, same-origin protected-route verification, and evidence-based status recording. v0.13.0 preview validation does not imply production promotion.

## Web Skia and interaction acceptance

React Native Skia uses CanvasKit/WASM on web. The build copies matching `canvaskit.wasm` into the public directory before export.

Browser acceptance covers mobile, tablet, desktop, animated Skia behavior, optical response inscription, reduced-graphics behavior, approved Work Specification → Code binding, hosted Google PKCE behavior, and conversation-native bounded-autonomy controls. Reduced-graphics mode must preserve the same Code/autonomy capability and stop-state semantics.

## Failure degradation

- Skia unavailable: preserve content/capability in the static reduced-graphics path.
- Google/Supabase identity provider unavailable: fail closed with sanitized sign-in recovery.
- Identity not enrolled, mismatched, or revoked: deny protected access.
- Browser session invalid/expired: return to identity gate without retaining provider/root credentials.
- Same-origin proxy unavailable: recoverable offline/private-session UI; never embed the root secret.
- Context cannot fit protected bounds: preserve the user turn and return a sanitized failure.
- Scope exhaustion: preserve the turn and fabricate no decision.
- Reason protected-invalid candidate: escalate provider/model route.
- Work Specification drafting failure: persist no fake revision.
- No approved Work Specification: block Code activation.
- Binding mismatch/digest conflict: block protected execution and preserve evidence.
- Bounded executor unavailable at PLAN: stop with `EXECUTOR_UNAVAILABLE` before plan mutation.
- Sandbox command failure/timeout: persist protected failed evidence and stop; never advance as success.
- Unsupported autonomous stage: return control at the explicit authority boundary.
- Database failure: `/ready` fails and deployment verification is blocked.
- Protected evaluation regression: block promotion.
- Preview regression: keep production on the last known-good deployment.

## Security

No provider secret, production root access secret, or Vercel execution credential is shipped to the client or sandbox. The Supabase project URL and publishable key remain public browser configuration, not authorization secrets.

Google identity proves who the user is; server-owned authorization decides what that identity may do. User/model content cannot redefine authentication, authorization, Work Specification approval, required acceptance criteria, executable commands, protected evaluation, execution policy, or deployment state.

The approved Work Specification binding is a trust boundary: the server owns its digest and acceptance map. The protected command registry is a second execution trust boundary: the server owns executable command definitions. The Vercel Sandbox is an isolation boundary: registered execution occurs away from the FastAPI host with deny-all networking and no application secrets.

Release claims remain traceable to versioned Git, CI/evaluation evidence, preview/production Vercel evidence, and explicit operator-controlled promotion state.
