# Parallax 2.0 Architecture

Version: 1.5
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo client plus a Python intelligence service. Reason 2.0 makes scope classification, deterministic context composition, protected verification, and observable failure evidence explicit architecture boundaries.

```text
Expo / React Native client
  ├─ normal accessible conversation text
  ├─ response state machine
  ├─ React Native Skia material + beam effects
  └─ SSE API client
          │
          ▼
FastAPI intelligence service
  ├─ conversation service + durable spec identity
  ├─ deterministic bounded context composer
  ├─ DSPy scope program
  ├─ protected scope policy
  ├─ DSPy Reason program
  ├─ Luna → Terra → Sol routers
  ├─ protected Reason verifier
  └─ observable execution/failure traces
          │
          ├───────────────► protected evaluation spine
          │                  ├─ development suites
          │                  ├─ promotion suites
          │                  ├─ deterministic scorer
          │                  ├─ evidence artifacts
          │                  └─ baseline/challenger gate
          ▼
SQLite (development) / dedicated Supabase PostgreSQL (P2 preview target)
```

## Core boundaries

### Client

The client owns interaction state and visual presentation. It does not own provider credentials, durable conversation truth, or material-scope authority.

Assistant content is rendered as standard React Native `Text`. Skia is used for living material, optical beam, glint, and decorative motion. This preserves accessibility and allows a no-Skia degradation path.

The response reducer is the single source of truth for `IDLE`, `THINKING`, `RESPONDING`, `VERIFYING`, `COMPLETE`, `SPEC_AMENDMENT`, and `ERROR`. Motion energy and laser activity are derived from that reducer, not from independent animation flags.

`SPEC_AMENDMENT` is a normal protected hand-off state, not a generic error. The client preserves the conversation and user turn, shows the concise server-provided amendment message, disables the optical inscription, and allows the user to continue once the objective/specification is appropriately resolved.

### Live response transport and optical typesetting

The response endpoint is consumed as server-sent events. `THINKING` and `RESPONDING` state events update the product state machine, while response chunks are appended to one growing assistant message.

The optical typesetter does **not** wait for the full response and replay it. It continuously chases the growing text target while the SSE stream remains open:

1. the API emits a response chunk;
2. the client appends the chunk to the active assistant message;
3. the line-aware typesetter reveals new characters behind the optical head;
4. wrapped-line geometry resets the head to the new active line;
5. only the newest glyph tail remains energized blue;
6. after the stream closes and the renderer catches up, the response enters `VERIFYING` and then `COMPLETE`.

For `SPEC_AMENDMENT`, no substantive response chunks are emitted. For recoverable protected failures, an SSE `error` event carries a sanitized public message and observable trace evidence without candidate text or hidden reasoning.

### API

Routes call services/coordinators. Services call repositories and intelligence adapters. Provider SDK details do not leak into route contracts.

The API exposes two operational probes with different meanings:

- `/health` proves the FastAPI process can answer requests;
- `/ready` executes a database `select 1` and proves the persistence dependency is reachable before deployment verification is claimed.

### Deterministic Reason context

`intelligence/context.py` composes the runtime Reason context from durable server state. It is provider-independent and deterministic.

The context contract preserves:

- conversation ID;
- active durable spec ID;
- lifecycle status;
- mode;
- current user turn;
- a bounded chronological window of prior messages;
- explicit user/assistant role markers;
- an authority rule stating that later explicit user corrections supersede conflicting older assistant statements or inferred assumptions.

Hard limits bound total characters, individual prior messages, current-turn length, and included prior-message count. Oldest eligible prior messages are removed first. The active spec and current user turn are never silently discarded. A SHA-256 digest, included-turn count, and truncation flag are retained as observable trace metadata.

### Scope authority

Normal product behavior does not trust a client Boolean as material-scope authority.

The DSPy scope program proposes one typed decision:

- `CONTINUE`;
- `CLARIFY`;
- `SPEC_AMENDMENT`.

A protected server policy validates the proposal and owns the transition semantics. Low-confidence `SPEC_AMENDMENT` proposals are conservatively converted to `CLARIFY` rather than silently mutating the approved objective. A transitional developer/test override exists only when `PARALLAX_ALLOW_SCOPE_OVERRIDE=true`; override use is explicit in the trace.

If all scope candidates fail provider execution or protected validation, no scope decision is fabricated. The public trace records `protected_scope_decision: null`, the attempted models/outcomes, `protected_verification_passed: false`, and final state `ERROR`.

### Reason program and protected verification

The DSPy Reason program receives the current objective, deterministic context, mode, active spec ID, and protected scope decision. Its typed observable result contains:

- user-facing answer;
- bounded confidence;
- bounded material uncertainties;
- bounded material assumptions;
- program version.

Observable uncertainty/assumption metadata is deliberately not hidden chain-of-thought.

Protected verification rejects malformed or unsafe results before completion. It enforces meaningful answer/clarification shape, confidence/metadata bounds, secret non-disclosure, no hidden reasoning payloads, and scope-specific requirements. A protected-invalid output is eligible for normal model escalation.

### Reason execution lifecycle

```text
USER TURN (durably preserved)
   ↓
DETERMINISTIC CONTEXT
   ↓
SCOPE ROUTER (Luna → Terra → Sol)
   ↓
PROTECTED SCOPE POLICY
   ├─ CONTINUE ─────► REASON ROUTER ─► PROTECTED VERIFY ─► RESPOND
   ├─ CLARIFY ──────► REASON ROUTER ─► one focused question ─► RESPOND
   └─ SPEC_AMENDMENT► durable status + hand-off message/event ─► STOP
```

If all Reason candidates fail after a protected scope decision has been established, the user turn remains durable and the API returns a recoverable error. The trace keeps the protected scope decision and model-attempt statuses but excludes candidate answer text, provider secrets, and hidden reasoning.

### Observable trace contract

Reason traces are evidence, not chain-of-thought. They include only observable execution metadata needed to explain system behavior:

- response/conversation/spec identity;
- mode;
- Reason and scope program versions when resolved;
- protected scope decision, nullable only when scope cannot be established;
- scope override and policy-adjustment indicators;
- context digest, turn count, and truncation indicator;
- attempted models and per-attempt status;
- protected verification outcome;
- final product state.

Invalid candidate text, DSPy rationale, hidden chain-of-thought, scratchpads, provider credentials, and environment values are excluded.

### Persistence and active specification identity

SQLAlchemy 2 models provide a development SQLite path and a PostgreSQL target path through `DATABASE_URL`.

Conversation identity is an opaque UUID. Messages are durable and ordered by creation time. Each conversation also stores its active specification identity. New conversations receive the configured `PARALLAX_ACTIVE_SPEC_ID`; existing conversations retain their historical stored spec ID when the product advances to a later release. This prevents a resumed conversation from silently changing its governing specification.

The P2 preview persistence target is a **dedicated Supabase PostgreSQL project**, separate from unrelated application databases. Vercel's ephemeral API functions connect through Supabase/Supavisor transaction pooling rather than maintaining application-side connection pools. Generic `postgres://` and `postgresql://` URLs are normalized to psycopg 3, prepared statements are disabled for transaction-pooler compatibility, and preview/production engines use SQLAlchemy `NullPool` so provider-side pooling remains authoritative.

The foundation still uses `Base.metadata.create_all()` for initial schema bootstrap. That is acceptable for an isolated preview but is not the long-term production migration strategy; schema evolution must move to explicit versioned migrations before a durable production release.

### Model routing

Runtime routing order remains:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Scope and Reason programs route independently under the same ordering. Escalation occurs on provider/program failure or protected validation failure. Attempt metadata is retained without model output payloads.

### DSPy development and optimization

DSPy is used in two distinct planes:

1. **Product runtime** — typed scope and Reason modules can be compiled/optimized without changing API contracts or protected policy.
2. **Parallax development** — specification compilation and critique are DSPy programs with explicit protected metrics.

The development plane must execute even when commercial provider credentials are absent. CI therefore supports two DSPy development-model paths:

- provider-backed model when an approved provider secret is configured;
- credential-free local Ollama model for required SpecCritic + SpecCompiler execution.

The local path proves that Parallax itself follows the DSPy build methodology; it is not the final quality authority. Provider-backed optimization such as MIPROv2 remains a separate challenger-production step, and every challenger must still pass protected promotion evidence before promotion.

Optimizer-controlled code cannot alter the protected acceptance/evaluation functions used to promote a compiled or optimized program.

### Code 2.0 execution kernel

Code mode owns a durable engineering run that is separate from, and immutably bound to, its durable conversation and approved specification. Protected server policy advances `SPECIFY → PLAN → IMPLEMENT → BUILD → TEST → VERIFY → REVIEW → COMPLETE`; pause, failure, amendment, cancellation, idempotent replay, and stale-revision conflict are explicit durable states or transitions.

The Code boundary consists of:

- append-only engineering attempts and safe evidence metadata;
- protected plan, implementation, execution, and review validators;
- provider-neutral workspace artifact identity using bounded paths, sizes, and SHA-256 digests;
- a deny-by-default typed execution contract and deterministic recorded executor for CI;
- API orchestration for create/get/latest/advance/pause/resume/cancel;
- a conversation-first client status surface whose semantics remain normal accessible text in reduced-graphics mode.

BUILD, TEST, and VERIFY cannot pass without successful execution evidence. IMPLEMENT cannot pass on prose alone. REVIEW compares its claimed workspace identity with independently persisted IMPLEMENT evidence and cannot authorize merge, deployment, or production status. A future live executor remains disabled by default and requires an explicit bounded workspace provider and command registry.

The API dependency range pins FastAPI to the validated `0.128.x` minor line. This prevents unreviewed framework/test-client drift from changing the release gate while still permitting patch-level security and compatibility updates.

## Protected evaluation spine

P2-V0.2.0 established evaluation as a first-class subsystem outside runtime DSPy program implementations. P2-V0.3.0 extends it with dedicated Reason development and promotion suites.

### Suite separation

Benchmark suites are versioned and have exactly one purpose:

- `development` — examples and metric feedback may be consumed by DSPy optimizers;
- `promotion` — protected evidence used only after a challenger is produced.

Promotion-suite expected contracts, thresholds, and protected decision rules are not optimizer inputs. A development-suite artifact is structurally incapable of authorizing promotion.

The general Parallax Engineering Benchmark covers specification fidelity, conversation continuity, implementation-plan completeness, protected-boundary preservation, failure/degradation handling, evidence/status honesty, secret handling, and concise engineering communication.

The Reason benchmark adds dedicated protected cases for multi-turn continuity, later correction precedence, material-scope containment, focused clarification, uncertainty/status honesty, secret handling, hidden-reasoning requests, concise communication, and all-model failure/degradation behavior.

### Deterministic scoring

`services/api/parallax_api/evaluation/` owns typed schemas, safe loading, deterministic protected scoring, evidence construction, and promotion comparison. Scoring is limited to explicitly declared contract behavior such as required coverage, forbidden behavior, exact protected assertions, case/category floors, and weighted aggregate scores. It does not silently award subjective quality points.

A higher aggregate score cannot compensate for a failed critical protected assertion or a protected category regression beyond the configured tolerance.

### Evidence contract

Evaluation artifacts are machine-readable evidence. They record suite/evaluator/program/model identity, input identity/digest, per-case results, failure reasons, category summaries, aggregate score, protected pass/fail, and an explicit no-chain-of-thought marker.

Candidate output is treated as untrusted text. Evidence and benchmark loaders reject secret-bearing content and hidden-reasoning fields. Protected evidence stores only the observable information required to explain the result.

### Promotion gate

The baseline/challenger comparison gate accepts only compatible promotion-suite artifacts. A challenger is rejected when it introduces a critical protected failure, misses a protected floor, exceeds aggregate/category regression tolerances, uses an incompatible evaluator version, or attempts to use development evidence for promotion.

Reason 2.0 includes recorded continuity, status-honesty, and material-scope regressions specifically to prove those failure modes are rejected.

Promotion remains an explicit engineering/release decision. Passing evaluation never automatically merges, deploys, changes protected thresholds, or rewrites authoritative records.

## Preview deployment topology

P2 preview deployment is isolated from the existing Parallax 1.x production Vercel project. The existing Vercel project named `parallax` is not a P2 deployment target and must not be overwritten, rebound, or used as a smoke-test destination.

P2 uses two dedicated Vercel preview projects from the same repository when preview deployment is authorized:

1. **P2 web** — project root `apps/client`; `npm run export:web`; static output `dist`.
2. **P2 API** — project root `services/api`; Vercel Python/FastAPI entrypoint `parallax_api.main:app`; SSE remains the response transport.

The web project receives only public client configuration such as `EXPO_PUBLIC_PARALLAX_API_URL`. The API project owns `DATABASE_URL`, provider credentials, `DSPY_MODEL`, `PARALLAX_ENV`, `PARALLAX_ACTIVE_SPEC_ID`, scope-override configuration, and CORS configuration.

Until application-level authentication is implemented, any P2 deployment connected to durable data or commercial model credentials must remain a protected preview rather than an intentionally public production service.

### Deployment verification

A deployment is not considered deployment-verified merely because a host reports `READY`. Evidence must cover:

- P2 web artifact loads at mobile, tablet, and desktop sizes;
- CanvasKit/Skia initializes and reduced-graphics degradation remains functional;
- P2 API `/health` succeeds;
- P2 API `/ready` succeeds against the dedicated PostgreSQL target;
- a conversation persists across separate API requests with the correct durable spec identity;
- ordinary Reason follow-ups preserve active context;
- SSE chunks arrive before completion and the optical typesetter visibly inscribes while the stream remains open;
- protected `SPEC_AMENDMENT` produces a calm hand-off with no substantive continuation;
- provider/protected-validation exhaustion returns a sanitized recoverable error and observable trace;
- no P1 deployment, domain, or project setting changed as part of P2 validation.

## Web Skia

React Native Skia uses CanvasKit/WASM on web. `apps/client/scripts/setup-skia-web.mjs` copies the matching `canvaskit.wasm` into the client public directory. Skia initialization is deferred on web before the application root is registered.

The browser acceptance gate verifies the Skia runtime and responsive layout at 390×844, 768×1024, and 1440×900. It also intentionally removes CanvasKit in a separate run to prove the static reduced-graphics fallback remains functional.

## Failure degradation

- Skia unavailable: show a static material fallback; conversation semantics remain functional.
- Context cannot fit protected bounds: preserve the durable user turn and return a sanitized recoverable context error.
- Scope provider/validation exhaustion: preserve the user turn, return recoverable `PROTECTED_SCOPE_FAILURE`, and record no fabricated protected scope decision.
- Protected Reason validation failure: continue Luna → Terra → Sol.
- Reason provider/validation exhaustion: preserve the user turn, return recoverable `PROTECTED_REASON_FAILURE`, and retain safe attempt evidence.
- Database failure: `/ready` returns a sanitized 503 and the system must not claim deployment verification or persisted conversation state.
- Commercial DSPy provider credentials unavailable during development: use the local DSPy compiler/critic path; do not claim provider-backed optimization.
- Evaluation challenger regresses a protected case/category: reject promotion and retain machine-readable reasons; do not compensate with a higher unrelated aggregate score.
- P2 preview regression: roll back the isolated P2 preview deployment without changing the P1 production project.

## Security

No model/provider secret is shipped to the client. Provider configuration is server-side environment only. CORS origins are configured explicitly or by a narrowly scoped preview-host regex. ORM-backed SQL is parameterized.

Conversation content is untrusted model input and cannot redefine protected scope policy, evaluation rules, or release state. Runtime traces exclude hidden chain-of-thought and candidate failure text. Structured scope factors, uncertainties, and assumptions are bounded observable metadata only.

P2 preview infrastructure must remain isolated from unrelated application databases and from the P1 production Vercel project. Protected preview access is required while application-level authentication is absent and durable data or provider credentials are attached.

The protected evaluation subsystem is also a trust boundary: optimizer code cannot import promotion authority as a writable configuration surface, benchmark/evidence artifacts must not contain secrets or hidden reasoning, and promotion claims must be traceable to versioned evidence.
