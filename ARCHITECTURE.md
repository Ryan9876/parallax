# Parallax 2.0 Architecture

Version: 1.1
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo client plus a Python intelligence service.

```text
Expo / React Native client
  ├─ normal accessible conversation text
  ├─ response state machine
  ├─ React Native Skia material + beam effects
  └─ SSE API client
          │
          ▼
FastAPI intelligence service
  ├─ conversation service
  ├─ persistence repositories
  ├─ DSPy reasoning program
  ├─ Luna → Terra → Sol router
  ├─ protected evaluators
  └─ observable execution traces
          │
          ▼
SQLite (development) / PostgreSQL (target)
```

## Core boundaries

### Client

The client owns interaction state and visual presentation. It does not own provider credentials or durable conversation truth.

Assistant content is rendered as standard React Native `Text`. Skia is used for living material, optical beam, glint, and decorative motion. This preserves accessibility and allows a no-Skia degradation path.

The response reducer is the single source of truth for `IDLE`, `THINKING`, `RESPONDING`, `VERIFYING`, `COMPLETE`, and `ERROR`. Motion energy and laser activity are derived from that reducer, not from independent animation flags.

### Live response transport and optical typesetting

The response endpoint is consumed as server-sent events. `THINKING` and `RESPONDING` state events update the product state machine, while response chunks are appended to one growing assistant message.

The optical typesetter does **not** wait for the full response and replay it. It continuously chases the growing text target while the SSE stream remains open:

1. the API emits a response chunk;
2. the client appends the chunk to the active assistant message;
3. the line-aware typesetter reveals new characters behind the optical head;
4. wrapped-line geometry resets the head to the new active line;
5. only the newest glyph tail remains energized blue;
6. after the stream closes and the renderer catches up, the response enters `VERIFYING` and then `COMPLETE`.

This keeps visible motion tied to actual system work rather than decorative playback after work has finished.

### API

Routes call services. Services call repositories and intelligence adapters. Provider SDK details do not leak into route contracts.

`ReasoningProgram` is an interface boundary. The initial implementation is DSPy-backed, but the API is insulated from compiled-program version changes.

### Persistence

SQLAlchemy 2 models provide a development SQLite path and a PostgreSQL-compatible target path through `DATABASE_URL`.

Conversation identity is an opaque UUID. Messages are durable and ordered by creation time.

### Model routing

Runtime routing order is fixed for the foundation release:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Escalation happens on provider failure or validation failure. Attempt metadata is retained in the response trace.

### DSPy development and optimization

DSPy is used in two distinct planes:

1. **Product runtime** — structured reasoning modules can be compiled/optimized without changing API contracts.
2. **Parallax development** — specification compilation and critique are DSPy programs with explicit protected metrics.

The development plane must execute even when commercial provider credentials are absent. CI therefore supports two DSPy development-model paths:

- provider-backed model when an approved provider secret is configured;
- credential-free local Ollama model for required SpecCritic + SpecCompiler execution.

The local path exists to prove and exercise the DSPy build methodology, not to establish the final quality ceiling. MIPROv2 promotion remains provider-backed in the v0.1.0 foundation because optimization quality is model-sensitive and every optimized artifact must still pass protected metrics before promotion.

Optimizer-controlled code cannot alter the protected acceptance/evaluation functions used to promote a compiled or optimized program.

## Web Skia

React Native Skia uses CanvasKit/WASM on web. `apps/client/scripts/setup-skia-web.mjs` copies the matching `canvaskit.wasm` into the client public directory. Skia initialization is deferred on web before the application root is registered.

The browser acceptance gate verifies the Skia runtime and responsive layout at 390×844, 768×1024, and 1440×900. It also intentionally removes CanvasKit in a separate run to prove the static reduced-graphics fallback remains functional.

## Failure degradation

- Skia unavailable: show a static material fallback; chat remains functional.
- Provider unavailable: router escalates through Luna, Terra, then Sol.
- All providers fail: preserve user message and return a recoverable error state.
- Database failure: return sanitized service error; never pretend a conversation was persisted.
- Commercial DSPy provider credentials unavailable during development: use the local DSPy compiler/critic path; do not claim provider-backed optimization.

## Security

No model/provider secret is shipped to the client. Provider configuration is server-side environment only. CORS origins are configured explicitly. ORM-backed SQL is parameterized. Execution traces exclude hidden chain-of-thought.
